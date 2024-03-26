// SPDX-License-Identifier: GPL-2.0-only
#define pr_fmt(fmt) KBUILD_MODNAME ": " fmt
#include <linux/module.h>
#include <linux/debugfs.h>
#include <linux/moduleparam.h>
#include <linux/kprobes.h>
#include <linux/min_heap.h>
#include <linux/ktime.h>

#define LOAD_BALANCE_FN_NAME "load_balance"
#define NUM_SAMPLES 1000UL

/* root debugfs directory for the module */
static struct dentry *dbgfs_root_dir;

/* collect samples if true */
static bool sampling = false;

typedef u64 samples_buffer_t[NUM_SAMPLES];

static DEFINE_PER_CPU(u64, timestamp);

static DEFINE_PER_CPU(struct min_heap, heap) = {
	.data = NULL,
	.nr = 0,
	.size = NUM_SAMPLES,
};

static DEFINE_PER_CPU(samples_buffer_t, samples_buffer);

static bool u64_less(const void *lhs, const void *rhs)
{
	return *(u64 *) lhs < *(u64 *) rhs;
}

static void u64_swap(void *lhs, void *rhs)
{
	u64 tmp;
	u64 *a = lhs, *b = rhs;

	tmp = *a;
	*a = *b;
	*b = tmp;
}

static const struct min_heap_callbacks heap_ops = {
	.elem_size = sizeof(u64),
	.less = u64_less,
	.swp = u64_swap,
};

static void add_sample(struct min_heap *h, u64 sample)
{
	if (h->nr < h->size)
		min_heap_push(h, &sample, &heap_ops);
	else if (*(u64 *) h->data < sample)
		min_heap_pop_push(h, &sample, &heap_ops);
}

static int load_balance_entry(struct kprobe *kp, struct pt_regs *regs)
{
	this_cpu_write(timestamp, ktime_get_ns());
	return 0;
}

static int load_balance_ret(struct kretprobe_instance *kp, struct pt_regs *regs)
{
	struct min_heap *samples;
	u64 sample;

	samples = get_cpu_ptr(&heap);

	sample = ktime_get_ns() - this_cpu_read(timestamp);
	add_sample(samples, sample);

	put_cpu_ptr(&heap);

	return 0;
}

/* the output buffer for when we read the "samples" file */
static char *output_buffer;
static size_t buffer_size;
static size_t buffer_len;

static ssize_t __format_buffer(size_t i, u64 value)
{
	ssize_t ret;

	while ((ret = snprintf(output_buffer + i, buffer_size, "%llu\n", value))
			>= buffer_size) {
		buffer_size *= 2;
		output_buffer = krealloc(output_buffer,
					 buffer_size, GFP_KERNEL);
		if (unlikely(!output_buffer))
		    return -ENOMEM;
	}

	return ret;
}

static ssize_t format_buffer(const u64 *samples, size_t count)
{
	ssize_t ret;
	size_t bi = 0;;

	if (!buffer_size) {
		buffer_size = 2 * sizeof(u64) * count + 1;
		output_buffer = kmalloc(buffer_size, GFP_KERNEL);
		if (unlikely(!output_buffer))
			return -ENOMEM;
	}

	output_buffer[0] = '\0';
	for (size_t i = 0; i < count; ++i) {
		ret = __format_buffer(bi, samples[i]);
		if (unlikely(ret < 0))
			return ret;
		bi += ret;
	}

	buffer_len = strlen(output_buffer);

	return 0;
}

static int summarize_samples(struct min_heap *h)
{
	unsigned int cpu;

	h->nr = 0;
	h->size = NUM_SAMPLES;
	h->data = kcalloc(NUM_SAMPLES, sizeof(u64), GFP_KERNEL);
	if (unlikely(!h->data))
		return -ENOMEM;

	for_each_online_cpu(cpu) {
		struct min_heap *p = per_cpu_ptr(&heap, cpu);
		const u64 *buff = p->data;

		for (size_t i = 0; i < p->nr; ++i)
			add_sample(h, buff[i]);
	}


	return 0;
}

static struct kprobe lb_entry = {
	.symbol_name = LOAD_BALANCE_FN_NAME,
	.flags = KPROBE_FLAG_DISABLED,
	.pre_handler = load_balance_entry,
};

static struct kretprobe lb_ret = {
	.kp = {
		.symbol_name = LOAD_BALANCE_FN_NAME,
		.flags = KPROBE_FLAG_DISABLED,
	},
	.handler = load_balance_ret,
	.maxactive = -1,
};

static ssize_t dbgfs_write_file_sampling(struct file *file, const char __user *user_buf,
					size_t count, loff_t *ppos)
{
	struct min_heap h;
	ssize_t ret;
	int retval;

	ret = debugfs_write_file_bool(file, user_buf, count, ppos);
	if (unlikely(ret < 0))
		return ret;

	if (sampling) {
		retval = enable_kprobe(&lb_entry);
		if (unlikely(retval < 0))
			pr_err("enable_kprobe failed: %d\n", retval);

		retval = enable_kretprobe(&lb_ret);
		if (unlikely(retval < 0))
			pr_err("enable_kretprobe failed: %d\n", retval);
	} else {
		retval = disable_kretprobe(&lb_ret);
		if (unlikely(retval < 0))
			pr_err("disable_kretprobe failed: %d\n", retval);

		retval = disable_kprobe(&lb_entry);
		if (unlikely(retval < 0))
			pr_err("disable_kprobe failed: %d\n", retval);

		if (!summarize_samples(&h)) {
			format_buffer(h.data, h.nr);
			kfree(h.data);
		}
	}

	return ret;
}

static const struct file_operations fops_sampling = {
	.read =		debugfs_read_file_bool,
	.write =	dbgfs_write_file_sampling,
	.open =		simple_open,
	.llseek =	default_llseek,
};

static ssize_t read_samples (struct file *file, char __user *user_buf,
			     size_t count, loff_t *ppos)
{
	ssize_t n;
	const loff_t pos = *ppos;

	if (unlikely(sampling))
		return -EBUSY;

	if (pos > buffer_len)
		return 0;

	n = min(count, buffer_len - pos);
	if (unlikely(copy_to_user(user_buf, output_buffer + pos, n)))
		return -EFAULT;
	*ppos += n;

	return n;
}

static const struct file_operations fops_samples = {
	.read =		read_samples,
	.open =		simple_open,
	.llseek =	default_llseek,
};

static int __init mod_init(void)
{
	struct dentry *entry;
	int ret;
	unsigned int cpu;

	dbgfs_root_dir = debugfs_create_dir(KBUILD_MODNAME, NULL);
	if (unlikely(IS_ERR(dbgfs_root_dir)))
		return PTR_ERR(dbgfs_root_dir);

	entry = debugfs_create_file("sampling", 0666, dbgfs_root_dir,
				    &sampling, &fops_sampling);
	if (unlikely(IS_ERR(entry))) {
		ret = PTR_ERR(entry);
		goto out;
	}

	entry = debugfs_create_file("samples", 0444, dbgfs_root_dir,
				    NULL, &fops_samples);
	if (unlikely(IS_ERR(entry))) {
		ret = PTR_ERR(entry);
		goto out;
	}

	ret = register_kprobe(&lb_entry);
	if (unlikely(ret < 0))
		goto out;

	ret = register_kretprobe(&lb_ret);
	if (unlikely(ret < 0))
		goto unreg_kprobe;

	for_each_possible_cpu(cpu)
		per_cpu_ptr(&heap, cpu)->data = per_cpu(samples_buffer, cpu);

	return 0;

unreg_kprobe:
	unregister_kprobe(&lb_entry);
out:
	debugfs_remove_recursive(dbgfs_root_dir);
	return ret;
}

static void __exit mod_exit(void)
{
	kfree(output_buffer);
	unregister_kretprobe(&lb_ret);
	unregister_kprobe(&lb_entry);
	debugfs_remove_recursive(dbgfs_root_dir);
}

module_init(mod_init);
module_exit(mod_exit);

MODULE_AUTHOR("Wander Lairson Costa");
MODULE_DESCRIPTION("A load balancer profiler");
MODULE_LICENSE("GPL");

#!/bin/bash -e

calc() {
    awk "BEGIN { print $* }"
}

# Parameters for exponential backoff retries
# The exponential backoff formula is given by:
#    random[1..2] * min_timeout * factor ^ attempts
max_timeout=240
min_timeout=1
attempts=10

# To avoid early saturation of the calculated sleep time, we must choose
# a value for factor that in the worst case scenario should not be
# greater than maxTimeout, i.e.:
#     2 * min_timeout * factor ^ attempts <= 30000
# Solving the equation for factor gives
#     factor = (max_timeout / 2) ^  (1 / attempts)
factor=$(calc "($max_timeout / 2.0) ** (1.0 / $attempts)")

random() {
	echo $(calc 1 + $RANDOM / 32000)
}

# Return the number of seconds to sleep based on the
# iteration. Returns an error if has reached the maximum number
# of retries.
exponenial_backoff() {
	i=$1
	if [ "$i" -gt $attempts ]; then
		echo "Maximum number of retries reached!!!" >&2
		return 1
	fi

	random_factor=$(random)
	pow=$(calc "$factor ** $i")
	echo $(calc "$(random) * $min_timeout * $pow")
}

run_test() {
    i=1
    echo "Run ktest for test case $1"
    while ! ./ktest.pl $1; do
        delay=$(exponenial_backoff $i)
        echo "ktest return failed, retrying in $delay seconds..." >&2
        sleep $(exponenial_backoff $i)
        ((i++))
    done
}

main() {
    for i in ktest_confs/*.conf; do
        run_test $i
    done;
}

main



#!/bin/bash -e

kerberos_renew=0

calc() {
    awk "BEGIN { print $* }"
}

renew_kerberos_ticket() {
    if [ $kerberos_renew -ne 0 ]; then
        kinit -R
    fi
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
        renew_kerberos_ticket
        delay=$(exponenial_backoff $i)
        echo "ktest return failed, retrying in $delay seconds..." >&2
        sleep $(exponenial_backoff $i)
        ((i++))
    done
}

run() {
    for i in ktest_confs/*.conf; do
        run_test $i
        renew_kerberos_ticket
    done;
}

while getopts ":k" opt; do
    case $opt in
        k)
            kerberos_renew=1
            ;;
        ?)
            echo "Invaid option -$OPTARG" >&2
            exit 1
    esac
done

run



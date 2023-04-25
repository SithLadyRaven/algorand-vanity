import argparse
import curses
import multiprocessing
import os.path
import re
import signal
import time
from algosdk import account, mnemonic
from multiprocessing import Process, Value, Manager

valid = re.compile('^[A-Z2-7]+$')
update_rate = 1/30
processes = []


def end_curses():
    if not curses.isendwin():
        curses.use_default_colors()
        curses.nocbreak()
        curses.echo()
        curses.curs_set(1)
        curses.endwin()


def signal_handler(sig, frame):
    terminate_processes(processes)
    end_curses()
    exit()



def terminate_processes(processes):
    for proc in processes:
        proc.terminate()


def check(vanity_str):
    return valid.match(vanity_str) is None


def calculate_expected_attempts(vanities):
    worst = 0
    for v in vanities:
        length = len(v)

        # each address character can be 1 of 32 possibilities
        expected = pow(32, length)
        if expected > worst:
            worst = expected
    return worst


def check_writable(filename):
    if os.path.exists(filename):
        if os.path.isfile(filename):
            return os.access(filename, os.W_OK)
        else:
            return False
    fdir = os.path.dirname(filename)
    if not fdir:
        fdir = '.'
    return os.access(fdir, os.W_OK)


def calculate_progress(current_attempts, expected_attempts):
    progress = (current_attempts/expected_attempts) * 100
    return progress


def get_color_pair(progress):
    if progress < 50:
        return curses.color_pair(30)
    elif progress < 90:
        return curses.color_pair(31)
    else:
        return curses.color_pair(32)



def output_result(filename, address, mnemonic):
    f = open(filename, "a")
    f.write(address + "\n")
    f.write(mnemonic + "\n")
    f.close()


def get_mnemonic(private_key):
    return mnemonic.from_private_key(private_key)


def generate_address(attempts, results, filename, output_lock):
    count = 0
    cont = True

    vanities = results.keys()

    while cont:
        count = count + 1
        if count == 100:
            with attempts.get_lock():
                attempts.value += 100
            count = 0

        private_key, address = account.generate_account()

        for v in vanities:
            if address.startswith(v):
                if results[v] == "":
                    mnemonic = get_mnemonic(private_key)
                    results[v] = (address, mnemonic)
                    with output_lock:
                        output_result(filename, address, mnemonic)


def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    parser = argparse.ArgumentParser(description="Algorand vanity address generator")
    parser.add_argument('vanity', nargs='+', type=str, help="String to look for")
    parser.add_argument('-t', '--threads', type=int, default=0,
                        help="Number of threads to use for processing. By default will use the # of available cores.")
    parser.add_argument('-l', '--location', type=str, choices=['start', 'end'],
                        help="Where to match the vanity string within the address", default="start")
    parser.add_argument('-f', '--filename', type=str, default="vanity_addresses")
    args = parser.parse_args()

    if not check_writable(args.filename):
        print("Output file is not writeable")
        print("Output file: " + args.filename)
        exit()

    manager = Manager()
    results = manager.dict()
    output_lock = manager.Lock()

    vanities = args.vanity
    longest = 0
    for v in vanities:
        if check(v):
            print("Invalid vanity string provided" + v +
                  ". Algorand addresses may only contain the letters A-Z and digits 2-7")
            exit()
        results[v] = ""
        if len(v) > longest:
            longest = len(v)

    attempts = Value('L', 0)

    start_time = time.time()

    proc_count = num_processors = multiprocessing.cpu_count()

    if args.threads > 0:
        proc_count = args.threads

    for i in range(proc_count):
        proc = Process(target=generate_address, args=(attempts, results, args.filename, output_lock))
        processes.append(proc)
        proc.start()

    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(30, curses.COLOR_BLACK, curses.COLOR_GREEN)
    curses.init_pair(31, curses.COLOR_BLACK, curses.COLOR_YELLOW)
    curses.init_pair(32, curses.COLOR_BLACK, curses.COLOR_RED)

    address = None
    private_key = None
    total_attempts = 0
    expected_attempts = calculate_expected_attempts(vanities)

    stdscr.addstr(0, 40, "Expected attempts: " + str(expected_attempts))
    remain = 0
    vanity = ""
    while True:
        time_diff = time.time()-start_time
        total_attempts = attempts.value

        if remain > 1:
            stdscr.addstr(0, 0, "Addresses remaining: {0}".format(remain))
        else:
            stdscr.addstr(0, 0, "Looking for: " + vanity)

        stdscr.addstr(1, 0, "Execution time: {:.2f}s".format(time_diff))
        stdscr.addstr(1, 40, "Addresses checked: " + str(attempts.value))

        aps = int(attempts.value/(time_diff + 1))

        stdscr.addstr(2, 0, "Attempts per second: {0}".format(aps))
        stdscr.clrtoeol()

        progress = calculate_progress(attempts.value, expected_attempts)

        stdscr.addstr(2, 40, "Current progress:")
        stdscr.addstr(2, 59, "{:.2f}%".format(progress), get_color_pair(progress))
        stdscr.clrtoeol()
        stdscr.addstr(4, 0, "Vanity status:")
        stdscr.refresh()

        time.sleep(update_rate)

        finished = True
        remain = 0
        line = 5

        for r in results:
            stdscr.addstr(line, 0, r)
            if results[r] == "":
                finished = False
                remain = remain + 1
                vanity = r
                stdscr.addstr(line, longest+2, "Searching")
                line = line + 1
            else:
                stdscr.addstr(line, longest+2, "Found!")
                line = line+1
            stdscr.clrtoeol()

        stdscr.refresh()
        if finished:
            break

    end_curses()

    print("All vanities found!")
    print("Total Addresses checked: " + str(total_attempts))
    print("Total execution time: {:.0f}s".format(time_diff))
    print("Attempts per second: " + str(aps))

    terminate_processes(processes)

if __name__ == "__main__":
    main()

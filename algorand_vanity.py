import argparse
import curses
import multiprocessing
import re
import signal
import time
from algosdk import account, mnemonic
from multiprocessing import Process, Value, Lock, Queue
from queue import Empty

valid = re.compile('^[A-Z2-7]+$')
update_rate = 1/30
processes = []

def signal_handler(sig, frame):
    terminate_processes()
    screen = save_screen(stdscr)
    curses.use_default_colors()
    curses.nocbreak()
    curses.echo()
    curses.curs_set(1)
    print_screen(screen)
    exit()

def terminate_processes():
    for proc in processes:
        proc.terminate()

def save_screen(stdscr):
    y, x = stdscr.getmaxyx()
    screen = []

    for row in range(y):
        line = str(stdscr.instr(row,0))
        line = line[2:len(line)-1].strip()
        if len(line) > 1:
            screen.append(line)
    return screen

def print_screen(screen):
    for line in screen:
        print(line)

def contains(vanity, address):
    return vanity in address

def check(vanity_str):
    return valid.match(vanity_str) is None

def calculate_expected_attempts(vanity):
    length = len(vanity)

    # each address character can be 1 of 32 possibilities
    expected = pow(32, length) 
    return expected

def calculate_progress(current_attempts, expected_attempts):
    progress = (current_attempts/expected_attempts) * 100
    return progress

def get_color_pair(progress):
    if progress < 50:
        return curses.color_pair(100)
    elif progress < 90:
        return curses.color_pair(101)
    else:
        return curses.color_pair(102)

def generate_address(vanity, attempts, queue, location):
    not_found = True

    while not_found:
        with attempts.get_lock():
            attempts.value += 1

        private_key, address = account.generate_account()

        match_method = {
            'start' : address.startswith,
            'end' : address.endswith,
        }

        if match_method[location](vanity):
            queue.put((address, private_key))
            not_found = False

if __name__ == "__main__":

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    parser = argparse.ArgumentParser(description="Algorand vanity address generator")
    parser.add_argument('vanity', type=str, help="String to look for")
    parser.add_argument('-t', '--threads', type=int, default=0, 
                        help="Number of threads to use for processing. By default will use the # of available cores.")
    parser.add_argument('-l', '--location', type=str, choices=['start', 'end'], help="Where to match the vanity string within the address", default="start")
    parser.add_argument('-o', '--output', action='store_true')
    args = parser.parse_args()

    vanity = args.vanity.upper()

    if check(vanity):
        print("Invalid vanity string provided. Algorand addresses may only contain the letters A-Z and digits 2-7")
        exit()

    attempts = Value('i', 0)
    queue = Queue()
    start_time = time.time()

    proc_count = num_processors = multiprocessing.cpu_count();

    for i in range(proc_count):
        proc = Process(target=generate_address, args=(vanity,attempts, queue, args.location))
        processes.append(proc)
        proc.start()

    stdscr = curses.initscr();
    curses.noecho()
    curses.cbreak()
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(100, curses.COLOR_BLACK, curses.COLOR_GREEN)
    curses.init_pair(101, curses.COLOR_BLACK, curses.COLOR_YELLOW)
    curses.init_pair(102, curses.COLOR_BLACK, curses.COLOR_RED)

    address = None
    private_key = None
    total_attempts = 0
    expected_attempts = calculate_expected_attempts(vanity)

    search_vanity = "Searching for: " + vanity
    stdscr.addstr(0, 0, search_vanity)
    stdscr.addstr(0, 40, "Expected attempts: " + str(expected_attempts))
    while address == None:
        time_diff = time.time()-start_time
        total_attempts = attempts.value

        stdscr.addstr(1, 0, "Execution time: {:.2f}s".format(time_diff))
        stdscr.addstr(1, 40, "Addresses checked: " + str(attempts.value))

        aps = int(attempts.value/(time_diff + 1))

        stdscr.addstr(2, 0, "Attempts per second: {0}s".format(aps))

        progress = calculate_progress(attempts.value, expected_attempts)

        stdscr.addstr(2, 40, "Current progress:")
        stdscr.addstr(2, 59, "{:.2f}%".format(progress), get_color_pair(progress))
        stdscr.clrtoeol()
        stdscr.refresh()

        time.sleep(update_rate)

        try:
            address, private_key = queue.get_nowait()
        except Empty:
            pass

    terminate_processes()

    address_mnemonic = mnemonic.from_private_key(private_key)

    stdscr.addstr(6, 0, "Total addresses checked: " + str(total_attempts))
    stdscr.addstr(7, 0, "Total execution time: {:.0f}s".format(time_diff))
    stdscr.addstr(8, 0, "Attempts per second: {}".format(aps))
    stdscr.addstr(10, 0, "Address: " + address)
    stdscr.addstr(11, 0, "Mnemonic: " + address_mnemonic)
    stdscr.addstr(20, 0, "")
    stdscr.refresh()

    screen = save_screen(stdscr)
    

    curses.use_default_colors()
    curses.nocbreak()
    curses.echo()
    curses.curs_set(1)
    curses.endwin()

    print_screen(screen)
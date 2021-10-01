import argparse
import curses
import multiprocessing
import re
import time
from algosdk import account, mnemonic
from multiprocessing import Process, Value, Lock, Queue

valid = re.compile('^[A-Z2-7]+$')

def check(vanity_str):
    return valid.match(vanity_str) is None

def update_screen(queue, attempts):
    while True:
        queue.put((None, None))
        time.sleep(0.05)

def generate_address(vanity, attempts, queue):
    not_found = True

    while not_found:
        with attempts.get_lock():
            attempts.value += 1

        private_key, address = account.generate_account()

        if address.startswith(vanity):
            queue.put((address, private_key))
            not_found = False

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Algorand vanity address generator")
    parser.add_argument("vanity", type=str, help="String to look for")
    parser.add_argument("-t", "--threads", type=int, default=0, 
                        help="Number of threads to use for processing. By default will use the # of available cores.")
    parser.add_argument("-l", "--location", type=str, choices=["start", "end", "any"], help="Where to match the vanity string within the address", default="start")
    args = parser.parse_args()

    vanity = args.vanity.upper()

    if check(vanity):
        print("Invalid vanity string provided. Algorand addresses may only contain the letters A-Z and digits 2-7")
        exit()
    print("Looking for ", vanity)

    attempts = Value('i', 0)
    queue = Queue()
    start_time = time.time()

    proc_count = num_processors = multiprocessing.cpu_count();
    processes = []

    for i in range(proc_count):
        proc = Process(target=generate_address, args=(vanity,attempts, queue))
        processes.append(proc)
        proc.start()

    proc = Process(target=update_screen, args=(queue, attempts))
    processes.append(proc)
    proc.start()

    stdscr = curses.initscr();
    curses.noecho()
    curses.cbreak()

    address = None
    private_key = None

    stdscr.addstr(0,0, "Attempting to find: " + vanity)
    while address == None:
        address, private_key = queue.get()
        time_diff = time.time()-start_time
        
        stdscr.addstr(1,0, "Addresses checked: {0}".format(attempts.value))
        stdscr.addstr(2,0, "Execution time: {0}s".format(int(time_diff)))

        aps = int(attempts.value/(time_diff + 1))

        stdscr.addstr(3,0, "Attempts per second: {0}s".format(aps))
        stdscr.clrtoeol()
        stdscr.refresh()

    for proc in processes:
        proc.terminate()

    stdscr.addstr(6,0, "Vanity found!")
    stdscr.addstr(7,0,  "Address: {0}".format(address))
    stdscr.addstr(8,0, "Mnemonic: {0}".format(mnemonic.from_private_key(private_key)))


    stdscr.addstr(11,0, "")

    stdscr.refresh()

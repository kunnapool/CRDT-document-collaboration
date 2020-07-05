from tkinter import *
import threading
import time
import sys
from xmlrpc.server import SimpleXMLRPCServer
import xmlrpc.client


root = Tk()
text = Text(root)
text.insert("0.0", "H")
text.pack()

MY_ADDR = ("localhost", int(sys.argv[1]))
HOST_ADDR = ("localhost", int(sys.argv[2]))

MY_OWNER_TAG = 'a'
if MY_ADDR[1] % 2 != 0:
    MY_OWNER_TAG = 'b'

LAMPORT_IDX = 0

ALL_DATA = []

CHANGED = False

mutex = threading.Lock()

def get_index():
    return "{}{}".format(LAMPORT_IDX, MY_OWNER_TAG)

class OpsBuffer():

    def __init__(self):
        self.ops_buffer = []
        self.num_ops = 0
        self.mutex = threading.Lock()
    
    def push_op_to_buffer(self, op):
        with self.mutex:
            self.ops_buffer.append(op)
            self.num_ops += 1
    
    def pop_op(self):
        with self.mutex:
            if self.num_ops > 0:
                op = self.ops_buffer[0]
                self.ops_buffer = self.ops_buffer[1:]
                self.num_ops -= 1

                return op
            
            return -1


class RpcServer(threading.Thread):

    def __init__(self):

        threading.Thread.__init__(self)
        self.port = MY_ADDR[1]
        self.addr = MY_ADDR[0]

        # serve other hosts using this
        self.server = SimpleXMLRPCServer((self.addr, self.port), allow_none=True)
        self.server.register_function(self.recv_ops)

    def run(self):
        self.server.serve_forever()

    def recv_ops(self, sender, IorD, val, idx, after):
        print("Sender sent {} {} at idx {} after {}".format(IorD, val, idx, after))

        global CHANGED
        insert_after(val, idx, after)

        mutex.acquire()
        text.delete("1.0", "end")
        text.insert("1.0", arr_to_ui_str())

        CHANGED = True

        mutex.release()
        return True


def send_ops(host_addr, op):

    IorD, val, idx, after = op
    # contact the other host using this
    proxy_addr = "http://{addr}:{port}/".format(addr=host_addr[0], port=host_addr[1])
    client_proxy = xmlrpc.client.ServerProxy(proxy_addr, allow_none=True)

    resp = client_proxy.recv_ops(MY_ADDR, IorD, val, idx, after)

def insert_after(val, idx, after):
    
    mutex.acquire()
    
    global ALL_DATA

    ALL_DATA.append( (val, idx, False) )

    # for i in range(len(ALL_DATA)):

        # v, ts, _ = ALL_DATA[i]

        # if ts > after and idx < ts:
        #     # shift right
        #     ALL_DATA.append( () ) # empty

        #     j = len(ALL_DATA)
        #     while j -1 != i: # shift everything right
        #         ALL_DATA[j-1] = ALL_DATA[j-2]
        #         j -= 1
            
        #     ALL_DATA[i] = (val, idx, False)

    mutex.release()


def insert_at_uiIdx_rc(r, c, x):

    global ALL_DATA
    global LAMPORT_IDX

    row = 0
    col = 0
    i = 0
    lmprt_idx = ""
    prv_idx = ""
    while True:

        if row == r - 1 and col == c:

            ALL_DATA.append( () ) # empty

            j = len(ALL_DATA)
            while j -1 != i: # shift everything right
                ALL_DATA[j-1] = ALL_DATA[j-2]
                j -= 1
            
            lmprt_idx = get_index()

            ALL_DATA[i] = (x, lmprt_idx, False)
            _, prv_idx, _ = ALL_DATA[i-1]
            LAMPORT_IDX += 1

            break
        
        val, ts, isDel = ALL_DATA[i]

        if val == '\n':
            row += 1
            col = 0
        elif not isDel:
            col += 1
        
        i += 1

    return prv_idx, lmprt_idx
    
        
def arr_to_ui_str():

    # mutex.acquire()
    global ALL_DATA

    i = 0
    s = []
    while i < len(ALL_DATA):

        val, _, isDel = ALL_DATA[i]

        if isDel == False:
            s.append(val)

        i += 1
    # mutex.release()
    return ''.join(s)

def editor():

    global LAMPORT_IDX
    global ALL_DATA
    global CHANGED

    ALL_DATA.append( ("H", "{}{}".format(LAMPORT_IDX, 'a'), False) ) # initialize common array
    LAMPORT_IDX += 1

    ops_buffer = OpsBuffer()
    rpc = RpcServer()
    rpc.start()

    last_line =""
    last_r = ""
    last_c = ""
    while True:
        CHANGED = False
        mutex.acquire()
        got_idx = (text.index(INSERT)).split(".")
        r, c = int(got_idx[0]), int(got_idx[1])
        curr_line = text.get("{}.0".format(r), "end")
        
        if CHANGED:
            last_line = curr_line
            continue

        if r != last_r: # moved to a diff line
            last_r = r
            last_line = curr_line
        elif CHANGED == False and last_line != curr_line: # insertion/deletion
            print(CHANGED, last_line, curr_line)
            traverse_idx = min(len(last_line), len(curr_line))

            # go through both lines and find diff
            ii = 0
            while ii < traverse_idx:
                if last_line[ii] != curr_line[ii]:
                    if len(curr_line) < len(last_line): # deletion

                        print("deleted {} - {}".format(last_line[ii], get_index()))
                        ops_buffer.push_op_to_buffer(("d", ii, last_line[ii]))
                        send_ops(HOST_ADDR, ("d", "{}.{}".format(r, c), last_line[ii]))

                    else: # insertion

                        prv_idx, cur_idx = insert_at_uiIdx_rc(r, c - 1, curr_line[ii] )
                        send_ops(HOST_ADDR, ("i", curr_line[ii], cur_idx, prv_idx))
                        # last_line = curr_line

                    break

                ii += 1
            last_line = curr_line
        print("ARR REP: ", arr_to_ui_str())
        mutex.release()
        time.sleep(0.1)

e = threading.Thread(target=editor)
e.start()
root.mainloop()
from tkinter import *
import threading
import time
import sys
from xmlrpc.server import SimpleXMLRPCServer
import xmlrpc.client

INTERNET = True

def myClick():
    global INTERNET
    global ops_buffer

    INTERNET = not INTERNET
    print("Button Clicked!!!", INTERNET)

    while True:
        op = ops_buffer.pop_op()

        if op == -1:
            break

        # IorD, val, idx, after = op
        send_ops(HOST_ADDR, op)

root = Tk()
text = Text(root)
button = Button(root, text="Toggle Internet!", command = myClick, fg="blue", bg="red")
text.insert("0.0", "H")
button.pack()
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

        def update_lamport(incoming_lmprt):
            global LAMPORT_IDX

            LAMPORT_IDX = max(LAMPORT_IDX, int(incoming_lmprt[0]))

        print("Sender sent {} {} at idx {} after {}".format(IorD, val, idx, after))

        mutex.acquire()
        global ALL_DATA
        global CHANGED
        
        update_lamport(idx)

        if IorD == "i":
            insert_after(val, idx, after)
        else:
            del_idx(idx)

        CHANGED = True

        mutex.release()

        return True


def send_ops(host_addr, op):

    print("Sending op: ", op)
    IorD, val, idx, after = op
    # contact the other host using this
    proxy_addr = "http://{addr}:{port}/".format(addr=host_addr[0], port=host_addr[1])
    client_proxy = xmlrpc.client.ServerProxy(proxy_addr, allow_none=True)

    resp = client_proxy.recv_ops(MY_ADDR, IorD, val, idx, after)

def insert_after(val, idx, after):
    
    global ALL_DATA

    for i in range(len(ALL_DATA)):

        v, ts, _ = ALL_DATA[i]

        if ts == after:
            print("\n\n", idx, ALL_DATA)
            moved = False
            while i + 1 < len(ALL_DATA) and idx < ALL_DATA[i+1][1]:
                print("{}<{}".format(idx, ALL_DATA[i+1][1]))
                i += 1
                moved = True

            print("\n\n")
            # shift right
            ALL_DATA.append( [] ) # empty

            j = len(ALL_DATA)
            while j -1 != i: # shift everything right
                ALL_DATA[j-1] = ALL_DATA[j-2]
                j -= 1

            ALL_DATA[i + 1] = [val, idx, False]

            break

def del_idx(idx):
    
    global ALL_DATA

    for i in range(len(ALL_DATA)):

        _, ts, _ = ALL_DATA[i]

        if ts == idx:

            ALL_DATA[i][2] = True # mark as deleted

            break


def insert_at_uiIdx_rc(r, c, x):
    """
    Insert val 'x' in the array at position p that corresponds
    to UI editor index (r, c)
    """

    global ALL_DATA
    global LAMPORT_IDX

    row = 0
    col = 0
    i = 0
    lmprt_idx = ""
    prv_idx = ""
    while True:

        if row == r - 1 and col == c - 1:

            ALL_DATA.append( [] ) # empty

            j = len(ALL_DATA)
            while j -1 != i: # shift everything right
                ALL_DATA[j-1] = ALL_DATA[j-2]
                j -= 1
            
            lmprt_idx = get_index()

            ALL_DATA[i] = [x, lmprt_idx, False]
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

def del_at_uiIdx_rc(r, c):

    global ALL_DATA

    row = 0
    col = 0
    i = 0
    lmprt_idx = ""
    prv_idx = ""

    while True:

        if row == r - 1 and col == c - 1:

            ALL_DATA[i][2] = True # mark as deleted
            lmprt_idx = ALL_DATA[i][1]
            prv_idx = ALL_DATA[i-1][1]

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
            s.append(str(val))

        i += 1
    # mutex.release()
    return ''.join(s)

def get_line_diff(last, curr):
    """assume insert for now"""

    # if there is a change
    if len(last) < len(curr): # insertion
        # insert in middle of sentence
        for idx in range(len(last)):
            if curr[idx] != last[idx]:
                return curr[idx], False
        # insert at end
        return curr[-1], False
    elif len(last) > len(curr): # deletion
        # deletion in middle of sentence
        for idx in range(len(curr)):
            if curr[idx] != last[idx]:
                return last[idx], True
        # deletion at end
        return last[-1], True
    else:
        # no change
        return "", None

ops_buffer = OpsBuffer()

def editor():

    def init_editor():
        # (re)initialize text editor window
        text.delete("1.0", "end")
        text.insert("1.0", arr_to_ui_str())

        last_line = text.get("1.0", "end").strip("\n")
        
        return last_line

    global LAMPORT_IDX
    global ALL_DATA
    global CHANGED
    global INTERNET

    ALL_DATA.append( ("H", "{}{}".format(LAMPORT_IDX, 'a'), False) ) # initialize common array
    LAMPORT_IDX += 1

    rpc = RpcServer()
    rpc.start()

    last_line = init_editor()
    last_r = ""
    last_c = ""

    while True:

        # get current index
        ui_cursor_row, ui_cursor_col = [int(x) for x in text.index("insert").split(".")]
        curr_line = text.get("{}.0".format(ui_cursor_row), "end").strip("\n")
        
        # by rpc
        if CHANGED:
            CHANGED = False
            curr_line = init_editor()
            last_line = curr_line

            continue
        
        line_diff, is_delted = get_line_diff(last_line, curr_line)

        # changed in editor
        if curr_line != last_line:
            IorD = ""
            if not is_delted:
                IorD = "i"
                prv_lmprt, curr_lmprt = insert_at_uiIdx_rc(ui_cursor_row, ui_cursor_col, line_diff)
            else:
                IorD = "d"
                prv_lmprt, curr_lmprt = del_at_uiIdx_rc(ui_cursor_row, ui_cursor_col + 1)
                print(prv_lmprt, curr_lmprt)
                pass
            
            if INTERNET:
                # IorD, val, idx, after = op
                send_ops(HOST_ADDR, (IorD, line_diff, curr_lmprt, prv_lmprt))
            else:
                ops_buffer.push_op_to_buffer((IorD, line_diff, curr_lmprt, prv_lmprt))


            # print("CHANGED")

            # re-init editor with arr contents
            curr_line = init_editor()
            last_line = curr_line

            
            text.mark_set("insert", "{}.{}".format(ui_cursor_row, ui_cursor_col))

        # print(ops_buffer.ops_buffer)

        last_line = curr_line
        time.sleep(0.1)

e = threading.Thread(target=editor)
e.start()
root.mainloop()
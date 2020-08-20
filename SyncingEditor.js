import React, { useMemo, useState, useEffect } from "react";
import { createEditor } from 'slate'
import { Slate, Editable, withReact } from 'slate-react'
import io from 'socket.io-client'
import { v4 as uuidv4 } from 'uuid';

// GoogleVM server
const socket = io.connect('https://34.121.79.252:4000')
const myUUID = uuidv4();

var LAMPORT_IDX = 0
const VAL_IDX = 0
const ID_IDX = 1
const AFTER_IDX = 2
const ISDEL_IDX = 3

var EditorCurrPosX = 0
var EditorCurrPosY = 1

var ALL_DATA = []
init()


function getLamportIdx() {
    return String(LAMPORT_IDX) + myUUID
}

function del_idx(idx) {
    for(let i=0; i<ALL_DATA.length; i++) {
        ts = ALL_DATA[i][ID_IDX]

        if (ts === idx) {
            ALL_DATA[i][ISDEL_IDX] = true
            break
        }
    }
}

function init() {

    var id = String(0) + myUUID

    // val, idx, after, isDel
    ALL_DATA.splice(0, 0, ['', 'X', null, false])
}

function arrToString(arr) {
    var str = ""

    for (let i = 0; i<arr.length; i++) {
        var val = arr[i][VAL_IDX]
        var isDel = arr[i][ISDEL_IDX]

        if (!isDel) {
            str += val
        }
    }

    return str
}

function updateXY (key) {
    if (key === 'ArrowLeft') EditorCurrPosX--
    else if (key === 'ArrowRight') EditorCurrPosX++
    else if (key === 'ArrowUp') EditorCurrPosY--
    else if (key === 'ArrowDown') EditorCurrPosY++
    else return false
    
    return true
}

function line_diff(last, curr) {
    if (last.length < curr.length) {
        for (let idx = 0; idx<last.length; idx++) {
            if (curr[idx] != last[idx]) {
                return curr[idx], false
            }
        }
        return curr[curr.length-1], false
    }
    else if (last.length > curr.length) {
        for (let idx = 0; idx<curr.length; idx++) {
            if (curr[idx] != last[idx]) {
                return last[idx], false
            }
        }
        return curr[last.length-1], false
    }
    else return "", null

}

function buffer_send() {
    
}

function insert (key){
    // start: insert at end

    var x = 0
    var y = 0
    var idx = 0

    EditorCurrPosX++

    // convert UI x, y into arr index
    for(idx = 0; idx<ALL_DATA.length; idx++) {
        var val = ALL_DATA[idx][VAL_IDX]
        var id = ALL_DATA[idx][ID_IDX]
        var isDel = ALL_DATA[idx][ISDEL_IDX]

        // we are in array where we are in UI
        if (x === EditorCurrPosX -1 && y === EditorCurrPosY -1) {
            var after_idx

            // predecessor for the very first element
            if (idx === 0) {
                after_idx = 'X'
                // idx = 1
            }
            else {
                after_idx = ALL_DATA[idx -1][ID_IDX]
            }

            var ele = [key, getLamportIdx(), after_idx, false]
            LAMPORT_IDX++

            // insert
            ALL_DATA.splice(idx, 0, ele)

            break
        }
        else if (val === '\n') {
            x = 0
            y++
        }
        // char is not deleted, i.e., is displayed on screen
        else if (!isDel) {
            x++
        }
    }

}

function updateEditorString(str) {
    return (
        [
            {
              type: 'paragraph',
              children: [{ text: str}],
            },
        ]
    )
}

export const SyncingEditor = () => {

    const editor = useMemo(() => withReact(createEditor()), [])

    // receive msgs from other peers here
    useEffect( () => {

        socket.on('message', msg => {
            if (msg.uuid !== myUUID) {
                console.log('Received ', msg.msg)
                ALL_DATA = msg.msg
            }
        });
    }, [ALL_DATA]);


    // initial display value
    const [value, setValue] = useState([
        {
          type: 'paragraph',
          children: [{ text: arrToString(ALL_DATA)}],
        },
    ])

    return (
        <Slate editor={editor} value={value} onChange={newValue => {
            // setValue(newValue)
            
            setValue(updateEditorString(arrToString(ALL_DATA)))
        } }>
            <Editable

            onKeyDown={ event => {
                // update where we are on editor
                if (!updateXY(event.key))
                    insert(event.key)

                console.log(ALL_DATA)
                // notify peers of change
                var msg = {
                    uuid: myUUID,
                    msg: arrToString(ALL_DATA)
                };
                socket.emit('message', msg)
                console.log('emitted')
            }}
            />
        </Slate>
    )
}

import React, { useMemo, useState, useEffect } from "react";
import { createEditor } from 'slate'
import { Slate, Editable, withReact } from 'slate-react'
import io from 'socket.io-client'
import { v4 as uuidv4 } from 'uuid';

const socket = io.connect('http://localhost:4000')
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

function init() {

    var id = String(0) + myUUID

    // val, idx, after, isDel
    ALL_DATA.splice(0, 0, ['', 'X', null, true])
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
    // inc can be negative
    if (key === 'ArrowLeft') EditorCurrPosX--
    else if (key === 'ArrowRight') EditorCurrPosX++
    else if (key === 'ArrowUp') EditorCurrPosY--
    else if (key === 'ArrowDown') EditorCurrPosY++
    else return false
    
    return true
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

        if (x === EditorCurrPosX -1 && y === EditorCurrPosY -1) {
            var after_idx

            if (idx === 0) {
                after_idx = 'X'
            }
            else {
                after_idx = ALL_DATA[idx -1][ID_IDX]
            }

            LAMPORT_IDX++
            var ele = [key, getLamportIdx(), after_idx, false]
            ALL_DATA.splice(idx, 0, ele)

            break
        }

        if (val === '\n') {
            x = 0
            y++
        }
        // char is not deleted, i.e., is displayed on screen
        if (!isDel) {
            x++
        }

    }

}

export const SyncingEditor = () => {

    const editor = useMemo(() => withReact(createEditor()), [])

    // receive msgs from other peers here
    useEffect( () => {

        socket.on('message', msg => {
            if (msg.uuid !== myUUID) {
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

    console.log(ALL_DATA)

    return (
        <Slate editor={editor} value={value} onChange={value => setValue(value)}>
            <Editable

            onKeyDown={ event => {
                
                // update where we are on editor
                if (!updateXY(event.key))
                    insert(event.key)

                console.log(ALL_DATA)
                // notify peers of change
                var msg = {
                    uuid: myUUID,
                    msg: event.key
                };
                socket.emit('message', msg)
            }}
            />
        </Slate>
    )
}

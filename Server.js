const app = require('express');
const http = require('http').Server(app);
const io = require('socket.io')(http);

io.on('connection', socket => {
    socket.on('message', msg => {
        io.emit('message', msg)
    });
});

http.listen(4000, function(){
    console.log("listening on 4000");
});
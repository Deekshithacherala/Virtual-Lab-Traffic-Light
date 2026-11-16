from flask import Flask, jsonify, request, render_template_string
import subprocess
import re

app = Flask(__name__)

VM1_IP = "172.31.18.202"
VM2_IP = "172.31.25.34"

demo_failure = False

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AWS Virtual Lab Network Monitor</title>

<style>
*{box-sizing:border-box;font-family:Arial,sans-serif}

body{
    margin:0;
    background:#0b1220;
    color:#f8fafc;
}

header{
    padding:20px 30px;
    background:#111827;
    border-bottom:1px solid #334155;
    display:flex;
    justify-content:space-between;
    align-items:center;
}

.title{
    font-size:24px;
    font-weight:bold;
}

.live{
    color:#22c55e;
    font-weight:bold;
}

.container{
    max-width:1100px;
    margin:auto;
    padding:25px;
}

.main{
    background:#172033;
    border-radius:18px;
    padding:30px;
    text-align:center;
}

.status{
    font-size:30px;
    font-weight:bold;
    margin:10px;
}

.green{color:#22c55e}
.yellow{color:#facc15}
.red{color:#ef4444}

.nodes{
    display:flex;
    justify-content:center;
    align-items:center;
    gap:35px;
    margin:30px 0;
}

.node{
    background:#0f172a;
    border:1px solid #334155;
    border-radius:14px;
    padding:20px;
    min-width:220px;
}

.node b{
    font-size:18px;
}

.ip{
    color:#94a3b8;
    margin-top:8px;
}

.arrow{
    font-size:40px;
    color:#38bdf8;
}

.cards{
    display:grid;
    grid-template-columns:repeat(3,1fr);
    gap:18px;
    margin-top:20px;
}

.card{
    background:#172033;
    border-radius:14px;
    padding:20px;
}

.label{
    color:#94a3b8;
    font-size:13px;
}

.value{
    font-size:28px;
    font-weight:bold;
    margin-top:8px;
}

.panel{
    background:#172033;
    border-radius:14px;
    padding:20px;
    margin-top:20px;
}

canvas{
    width:100%;
    height:180px;
    background:#0f172a;
    border-radius:10px;
}

button{
    border:0;
    border-radius:9px;
    padding:13px 20px;
    margin:5px;
    font-weight:bold;
    cursor:pointer;
}

.failure{
    background:#ef4444;
    color:white;
}

.restore{
    background:#22c55e;
    color:#052e16;
}

.event{
    padding:9px;
    border-bottom:1px solid #334155;
    color:#cbd5e1;
}

.info{
    color:#cbd5e1;
    line-height:1.8;
}

@media(max-width:700px){
    .cards{grid-template-columns:1fr}
    .nodes{flex-direction:column}
    .arrow{transform:rotate(90deg)}
}
</style>
</head>

<body>

<header>
    <div class="title">☁ AWS Virtual Lab Network Monitor</div>
    <div class="live">● LIVE</div>
</header>

<div class="container">

<div class="main">

    <div id="status" class="status green">
        🟢 NETWORK HEALTHY
    </div>

    <div class="nodes">

        <div class="node">
            <b>VM1 — MONITOR</b>
            <div class="ip">172.31.18.202</div>
        </div>

        <div class="arrow">→</div>

        <div class="node">
            <b>VM2 — TARGET</b>
            <div class="ip">172.31.25.34</div>
        </div>

    </div>

    <button class="failure" onclick="demoFailure()">
        🧪 Simulate Failure
    </button>

    <button class="restore" onclick="restoreNetwork()">
        ↻ Restore Network
    </button>

</div>

<div class="cards">

    <div class="card">
        <div class="label">LATENCY</div>
        <div id="latency" class="value">-- ms</div>
    </div>

    <div class="card">
        <div class="label">PACKET LOSS</div>
        <div id="loss" class="value">-- %</div>
    </div>

    <div class="card">
        <div class="label">CONNECTION</div>
        <div id="connection" class="value">CHECKING...</div>
    </div>

</div>

<div class="panel">
    <h2>📈 Live Network Performance</h2>
    <canvas id="chart" width="900" height="180"></canvas>
</div>

<div class="panel">
    <h2>🕐 Recent Events</h2>
    <div id="events">Starting monitor...</div>
</div>

<div class="panel info">
    <h2>☁ AWS Infrastructure</h2>
    <b>Platform:</b> Amazon EC2<br>
    <b>Monitor:</b> VM1<br>
    <b>Target:</b> VM2<br>
    <b>Protocol:</b> ICMP / Ping<br>
    <b>Purpose:</b> Real-time cloud network health monitoring
</div>

</div>

<script>

let history=[];
let events=[];

function addEvent(message){

    const time=new Date().toLocaleTimeString();

    events.unshift(time+" — "+message);

    events=events.slice(0,6);

    document.getElementById("events").innerHTML=
        events.map(x=>"<div class='event'>"+x+"</div>").join("");
}

function update(){

    fetch("/api/status")
    .then(r=>r.json())
    .then(data=>{

        document.getElementById("latency").innerText=
            data.latency+" ms";

        document.getElementById("loss").innerText=
            data.packet_loss+" %";

        const connection=
            document.getElementById("connection");

        const status=
            document.getElementById("status");

        if(data.connected){

            connection.innerText="CONNECTED";

            if(data.latency>100){

                status.className="status yellow";
                status.innerText="🟡 HIGH LATENCY";

            }else{

                status.className="status green";
                status.innerText="🟢 NETWORK HEALTHY";
            }

        }else{

            connection.innerText="DISCONNECTED";

            status.className="status red";
            status.innerText="🔴 NETWORK DOWN";
        }

        history.push(data.latency);

        if(history.length>40)
            history.shift();

        draw();

    })
    .catch(()=>{

        document.getElementById("connection").innerText="ERROR";

    });
}

function draw(){

    const canvas=document.getElementById("chart");
    const ctx=canvas.getContext("2d");

    ctx.clearRect(0,0,canvas.width,canvas.height);

    if(history.length<2)
        return;

    const max=Math.max(...history,1);

    ctx.beginPath();

    history.forEach((v,i)=>{

        const x=i*(canvas.width/40);

        const y=
            canvas.height-
            (v/max)*(canvas.height-20)-10;

        if(i===0)
            ctx.moveTo(x,y);
        else
            ctx.lineTo(x,y);

    });

    ctx.strokeStyle="#38bdf8";
    ctx.lineWidth=3;
    ctx.stroke();
}

function demoFailure(){

    fetch("/api/demo",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({failure:true})
    });

    addEvent("⚠ Demo failure activated");
}

function restoreNetwork(){

    fetch("/api/demo",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({failure:false})
    });

    addEvent("✓ Network restored");
}

addEvent("AWS monitoring started");

update();

setInterval(update,2000);

</script>

</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/api/status")
def status():

    global demo_failure

    if demo_failure:

        return jsonify({
            "connected":False,
            "latency":0,
            "packet_loss":100
        })

    result=subprocess.run(
        ["ping","-c","1","-W","1",VM2_IP],
        capture_output=True,
        text=True
    )

    if result.returncode==0:

        match=re.search(
            r"time[=<]([0-9.]+)",
            result.stdout
        )

        latency=float(match.group(1)) if match else 0

        return jsonify({
            "connected":True,
            "latency":round(latency,3),
            "packet_loss":0
        })

    return jsonify({
        "connected":False,
        "latency":0,
        "packet_loss":100
    })

@app.route("/api/demo",methods=["POST"])
def demo():

    global demo_failure

    data=request.get_json(silent=True) or {}

    demo_failure=bool(data.get("failure",False))

    return jsonify({"ok":True})

if __name__=="__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )

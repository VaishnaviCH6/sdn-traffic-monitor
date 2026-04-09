from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.recoco import Timer

log = core.getLogger()
mac_to_port = {}
connections = []

def _handle_ConnectionUp(event):
    log.info("Switch %s connected!" % (event.dpid))
    connections.append(event.connection)

def _handle_PacketIn(event):
    packet = event.parsed
    dpid = event.connection.dpid

    if dpid not in mac_to_port:
        mac_to_port[dpid] = {}

    src = packet.src
    dst = packet.dst
    in_port = event.port

    mac_to_port[dpid][src] = in_port

    if dst in mac_to_port[dpid]:
        out_port = mac_to_port[dpid][dst]
    else:
        out_port = of.OFPP_FLOOD

    # Install flow
    msg = of.ofp_flow_mod()
    msg.match.dl_src = src
    msg.match.dl_dst = dst
    msg.actions.append(of.ofp_action_output(port=out_port))
    msg.idle_timeout = 10
    msg.hard_timeout = 30

    event.connection.send(msg)

    # Forward packet
    packet_out = of.ofp_packet_out()
    packet_out.data = event.ofp
    packet_out.actions.append(of.ofp_action_output(port=out_port))
    event.connection.send(packet_out)

def request_stats():
    for conn in connections:
        req = of.ofp_stats_request(body=of.ofp_flow_stats_request())
        conn.send(req)

def _handle_FlowStatsReceived(event):
    with open("traffic_report.txt", "a") as f:
        f.write("\n===== TRAFFIC REPORT =====\n")

        print("\n===== TRAFFIC REPORT =====")

        for stat in event.stats:
            if stat.packet_count > 0:
                line = (f"{stat.match.dl_src} -> {stat.match.dl_dst} | "
                        f"Packets: {stat.packet_count} | Bytes: {stat.byte_count}")

                print(line)
                f.write(line + "\n")

        print("==========================\n")
        f.write("==========================\n")

def launch():
    core.openflow.addListenerByName("ConnectionUp", _handle_ConnectionUp)
    core.openflow.addListenerByName("PacketIn", _handle_PacketIn)
    core.openflow.addListenerByName("FlowStatsReceived", _handle_FlowStatsReceived)

    Timer(5, request_stats, recurring=True)

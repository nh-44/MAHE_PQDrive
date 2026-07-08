import time

class CANBus:
    """
    Minimal CAN bus simulator.
    In a real vehicle, ECU domain controllers communicate over CAN/CAN-FD.
    Here we model message passing so the dashboard can visualise bus traffic.
    """

    def __init__(self):
        self.messages = []   # list of dicts — full audit trail

    def send(self, sender: str, receiver: str, msg_type: str, data: dict) -> dict:
        frame = {
            "timestamp": time.time(),
            "sender":    sender,
            "receiver":  receiver,
            "type":      msg_type,
            "data":      data,
        }
        self.messages.append(frame)
        return frame

    def broadcast(self, sender: str, msg_type: str, data: dict) -> dict:
        return self.send(sender, "BROADCAST", msg_type, data)

    def get_log(self, msg_type: str = None) -> list:
        if msg_type is None:
            return self.messages
        return [m for m in self.messages if m["type"] == msg_type]

    def clear(self):
        self.messages = []

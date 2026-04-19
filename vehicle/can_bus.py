"""ZeroMQ-based CAN bus simulation for inter-process messaging."""

from __future__ import annotations

import json

import zmq


class CANBus:
	"""Simple PUB/SUB wrapper to simulate CAN-style topic messaging."""

	def __init__(self, pub_port: int = 5555, sub_port: int = 5556) -> None:
		self.context = zmq.Context()
		self.pub_port = pub_port
		self.sub_port = sub_port

		self.pub_socket = self.context.socket(zmq.PUB)
		self.pub_socket.bind(f"tcp://127.0.0.1:{self.pub_port}")

		self.sub_socket = self.context.socket(zmq.SUB)
		self.sub_socket.connect(f"tcp://127.0.0.1:{self.pub_port}")

	def publish(self, topic: str, message: dict) -> None:
		"""Publish one topic-scoped JSON message on the simulated bus."""
		payload = json.dumps(message)
		self.pub_socket.send_string(f"{topic} {payload}")

	def subscribe(self, topic: str) -> dict:
		"""Subscribe to one topic and receive a single JSON message."""
		self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, topic)
		raw = self.sub_socket.recv_string()
		_, payload = raw.split(" ", 1)
		return json.loads(payload)

	def close(self) -> None:
		"""Close sockets and terminate ZeroMQ context."""
		self.pub_socket.close(0)
		self.sub_socket.close(0)
		self.context.term()

"""
    PyHSS GSUP Client for testing

    This file is not really a unit test, but a client that connects to the GSUP server
    It helped during the development of the GSUP server to test the messages and
    this file has been left here in the hope that it may be useful.

    Copyright (C) 2025  Lennart Rosam <hello@takuto.de>
    Copyright (C) 2025  Alexander Couzens <lynxis@fe80.eu>

    SPDX-License-Identifier: AGPL-3.0-or-later

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published
    by the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import socket

from osmocom.gsup.message import MsgType, GsupMessage

from gsup.protocol.gsup_msg import GsupMessageBuilder, GsupMessageUtil
from gsup.protocol.osmocom_ipa import IPA



class GSUPClient:
    def __init__(self, server_ip, server_port, identity='SGSN'):
        self.server_ip = server_ip
        self.server_port = server_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ipa = IPA()
        self.identity = identity

    def connect(self):
        self.sock.connect((self.server_ip, self.server_port))

        # Receive the identity request from server
        identity = self.sock.recv(3)
        payload_length = int.from_bytes(identity[0:2], 'big')
        protocol = self.ipa.proto(identity[2])

        if protocol != 'CCM':
            socket.close()
            raise ValueError(f"Unsupported protocol: {protocol}")

        payload = self.sock.recv(payload_length)
        msg_type = self.ipa.msgt(payload[0])

        if msg_type != 'ID_GET':
            socket.close()
            raise ValueError(f"Unsupported message type: {msg_type}")

        # Send the identity response to the server
        data = self.ipa.tag_unit(self.identity.encode('utf-8'))
        data = self.ipa.id_resp(data)
        self.sock.send(data)

        # Check if server acked the identity response
        ack_hdr = self.sock.recv(3)
        payload_length = int.from_bytes(identity[0:2], 'big')
        protocol = self.ipa.proto(identity[2])
        if protocol != 'CCM':
            self.sock.close()
            raise ValueError(f"Unsupported protocol: {protocol}")

        ack = self.sock.recv(payload_length)
        msg_type = self.ipa.msgt(ack[0])
        if msg_type != 'ID_ACK':
            self.sock.close()
            raise ValueError(f"Unexpected ACK message: {msg_type}")

    def send_auth_info_request(self, imsi):
        request = (GsupMessageBuilder()
         .with_msg_type(MsgType.SEND_AUTH_INFO_REQUEST)
         .with_ie('imsi', imsi)
         .with_ie('cn_domain', 'ps')
         ).build()

        data = self.ipa.add_header(request.to_bytes(), self.ipa.PROTO['OSMO'], self.ipa.EXT['GSUP'])
        self.sock.send(data)

        response = self.__read_response()

        print(f"Received response: {response.to_dict()}")

    def send_ulr_request(self, imsi):
        request = (GsupMessageBuilder()
         .with_msg_type(MsgType.UPDATE_LOCATION_REQUEST)
         .with_ie('imsi', imsi)
         .with_ie('cn_domain', 'ps')
        ).build()

        data = self.ipa.add_header(request.to_bytes(), self.ipa.PROTO['OSMO'], self.ipa.EXT['GSUP'])
        self.sock.send(data)

        response = self.__read_response()
        print(f"Received response: {response.to_dict()}")

        if response.msg_type != MsgType.INSERT_DATA_REQUEST:
            print(f"Received error response: {response.msg_type()}")
            return

        # Send the insert data response
        insert_data_resp = (GsupMessageBuilder()
         .with_msg_type(MsgType.INSERT_DATA_RESULT)
         .with_ie('imsi', imsi)
         .with_ie('cn_domain', 'ps')
        ).build()

        data = self.ipa.add_header(insert_data_resp.to_bytes(), self.ipa.PROTO['OSMO'], self.ipa.EXT['GSUP'])
        self.sock.send(data)

        response = self.__read_response()
        print(f"Received response: {response.to_dict()}")

    def wait_for_location_cancel(self):
        response = self.__read_response()
        print(f"Received response: {response.to_dict()}")

        if response.msg_type != MsgType.LOCATION_CANCEL_REQUEST:
            print(f"Received error response: {response.msg_type()}")
            return

        # Send the location cancel response
        cancel_resp = (GsupMessageBuilder()
         .with_msg_type(MsgType.LOCATION_CANCEL_RESULT)
         .with_ie('imsi', GsupMessageUtil.get_first_ie_by_name('imsi', response.to_dict()))
        ).build()

        data = self.ipa.add_header(cancel_resp.to_bytes(), self.ipa.PROTO['OSMO'], self.ipa.EXT['GSUP'])
        self.sock.send(data)

    def send_purge_ue(self, imsi):
        request = (GsupMessageBuilder()
         .with_msg_type(MsgType.PURGE_MS_REQUEST)
         .with_ie('imsi', imsi)
        ).build()

        data = self.ipa.add_header(request.to_bytes(), self.ipa.PROTO['OSMO'], self.ipa.EXT['GSUP'])
        self.sock.send(data)

        response = self.__read_response()
        print(f"Received response: {response.to_dict()}")

    def __read_response(self) -> GsupMessage:
        resp_hdr = self.sock.recv(3)
        payload_length = int.from_bytes(resp_hdr[0:2], 'big')
        payload = self.sock.recv(payload_length)
        response = GsupMessage.from_bytes(payload[1:])
        return response


    def disconnect(self):
        self.sock.close()



if __name__ == '__main__':
    client = GSUPClient('127.0.0.1', 4222, 'SGSN-NG')
    client2 = GSUPClient('127.0.0.1', 4222, 'SGSN')

    client.connect()
    client2.connect()

    client.send_auth_info_request('262423403000001')
    client.send_ulr_request('262423403000001')

    #client2.wait_for_location_cancel()
    client.send_purge_ue('262423403000001')

    client.disconnect()
    client2.disconnect()
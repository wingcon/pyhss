"""
    PyHSS GSUP Message Builder - A factory class to create new GSUP Messages
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

from osmocom.gsup.message import MsgType, GsupMessage


class GsupMessageBuilder:
    def __init__(self):
        self.gsup_dict = dict()
        self.gsup_dict['ies'] = list()
        self.gsup_dict['msg_type'] = ""

    def with_msg_type(self, msg_type: MsgType):
        self.gsup_dict['msg_type'] = msg_type.name
        return self

    def with_ie(self, name: str, value):
        if 'ies' not in self.gsup_dict:
            self.gsup_dict['ies'] = []

        for ie in self.gsup_dict['ies']:
            if name in ie and isinstance(ie[name], list) and isinstance(value, dict):
                ie[name].append(value)
                return self
            elif name in ie and isinstance(ie[name], list) and isinstance(value, list):
                ie[name].extend(value)
                return self


        self.gsup_dict['ies'].append({
            name: value
        })
        return self

    def with_msisdn_ie(self, msisdn: str):
        ie = {
            'bcd_len': (len(msisdn) + 1) // 2,
            'digits': msisdn
        }
        return self.with_ie('msisdn', ie)

    def with_pdp_info_ie(self, pdp_ctx_id: int, pdp_type: str, apn_name: str):
        pdp_info = GsupMessageUtil.get_first_ie_by_name('pdp_info', self.gsup_dict)
        if pdp_info is None:
            pdp_info = []

        pdp_info.append({
            'pdp_context_id': pdp_ctx_id
        })

        pdp_info.append({
            'pdp_address': {
                'address': None,
                'hdr': {
                    'pdp_type_nr': pdp_type,
                    'pdp_type_org': 'ietf'
                }
            }
        })

        pdp_info.append(
            {
                'access_point_name': apn_name
            }
        )

        pdp_info.append({'qos': None})

        return self.with_ie('pdp_info', pdp_info)

    def build(self) -> GsupMessage:
        if 'msg_type' == "":
            raise ValueError("msg_type is required")
        return GsupMessage.from_dict(self.gsup_dict)


class GsupMessageUtil:
    GSUP_MSG_IES = "ies"
    GSUP_MSG_IE_IMSI = "imsi"
    GSUP_MSG_IE_AUTH_TUPLE = "auth_tuple"

    @staticmethod
    def get_first_ie_by_name(ie_name: str, message: dict):
        for ie in message['ies']:
            if ie_name in ie:
                return ie[ie_name]
        return None

    @staticmethod
    def get_ies_by_name(ie_name: str, message: dict):
        ies = []
        for ie in message['ies']:
            if ie_name in ie:
                ies.append(ie)
        return ies

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os

import trustme

from pifpaf import drivers


class TrustMeDriver(drivers.Driver):
    def __init__(
        self,
        client_identity=None,
        server_identity=None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.client_identity = client_identity
        self.server_identity = server_identity

    @classmethod
    def get_options(cls):
        return [
            {
                "param_decls": ["--client_identity"],
                "default": "client@example.org",
                "help": "The identity that this certificate will be valid "
                        "for. Most commonly, this is just a hostname, the "
                        "following forms are accepted: "
                        "Regular hostname (example.com), "
                        "Wildcard hostname (*.example.com), "
                        "International Domain Name (café.example.com), "
                        "IDN in A-label form (xn--caf-dma.example.com), "
                        "IPv4 address (127.0.0.1), "
                        "IPv6 address (::1), "
                        "IPv4 network (10.0.0.0/8), "
                        "IPv6 network (2001::/16), "
                        "Email address (example@example.com). "
                        'This ultimately end up as a "Subject Alternative '
                        'Name", which are what modern programs are supposed '
                        "to use when checking identity.",
            },
            {
                "param_decls": ["--server_identity"],
                "default": "localhost",
                "help": "Likewise client_identity.",
            },
        ]

    def _setUp(self):
        super()._setUp()

        self.generate_chain(self.client_identity, "client")
        self.generate_chain(self.server_identity, "server")

    def generate_chain(self, identity, prefix):
        authority = trustme.CA()
        identity = authority.issue_cert(identity)

        ca_path = os.path.join(self.tempdir, f"{prefix}-ca.pem")
        key_path = os.path.join(self.tempdir, f"{prefix}-key.pem")
        cert_path = os.path.join(self.tempdir, f"{prefix}-cert.pem")

        authority.cert_pem.write_to_path(ca_path)
        identity.private_key_pem.write_to_path(key_path)
        identity.cert_chain_pems[0].write_to_path(cert_path)

        self.putenv(f"{prefix.upper()}_CA", ca_path)
        self.putenv(f"{prefix.upper()}_KEY", key_path)
        self.putenv(f"{prefix.upper()}_CERT", cert_path)

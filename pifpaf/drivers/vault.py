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

import uuid

from pifpaf import drivers


class VaultDriver(drivers.Driver):
    DEFAULT_ROOT_TOKEN_ID = str(uuid.uuid4())
    DEFAULT_LISTEN_ADDRESS = "127.0.0.1:8200"

    def __init__(self, root_token_id=DEFAULT_ROOT_TOKEN_ID,
                 listen_address=DEFAULT_LISTEN_ADDRESS, **kwargs):
        """Create a new Vault instance."""
        super(VaultDriver, self).__init__(**kwargs)
        self.root_token_id = root_token_id
        self.listen_address = listen_address

    @classmethod
    def get_parser(cls, parser):
        parser.add_argument("--root-token-id",
                            default=cls.DEFAULT_ROOT_TOKEN_ID,
                            help="root token for vault")
        parser.add_argument("--listen-address",
                            default=cls.DEFAULT_LISTEN_ADDRESS,
                            help="listen address for vault")
        return parser

    def _setUp(self):
        super(VaultDriver, self)._setUp()
        c, _ = self._exec(["vault",
                           "server",
                           "-dev",
                           "-dev-root-token-id=" + self.root_token_id,
                           "-dev-listen-address=" + self.listen_address],
                          wait_for_line="Vault server started!")

        self.putenv("ROOT_TOKEN", self.root_token_id)
        self.putenv("VAULT_ADDR", "http://%s" % self.listen_address)
        self.putenv("URL", "http://%s" % self.listen_address)

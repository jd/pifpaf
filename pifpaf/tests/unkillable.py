# -*- encoding: utf-8 -*-
#
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

import argparse
import os
import signal
import threading

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--child-only', action='store_true')
    parser.add_argument('--exited-parent', action='store_true')
    args = parser.parse_args()

    pid = os.fork()
    if pid == 0:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        # Wait forever
        threading.Event().wait()
    else:
        if not args.child_only:
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
        print("started")
        if not args.exited_parent:
            # Wait for child
            os.waitpid(pid, 0)

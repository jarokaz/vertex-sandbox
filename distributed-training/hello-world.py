# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import json
import pprint

pp = pprint.PrettyPrinter(indent=4)


def main():

    env_vars = dict(os.environ) 
    print('Environment variables:')
    pp.pprint(env_vars)
    cluster_spec = os.getenv('CLUSTER_SPEC')
    if cluster_spec:
        cluster_spec = json.loads(cluster_spec)
        print('CLUSTER_SPEC:')
        pp.pprint(cluster_spec)
    else:
        print('No CLUSTER_SPEC variable in the environment')

if __name__ == '__main__':
    main()

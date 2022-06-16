#!/usr/bin/python3 -B

# Copyright 2021 Josh Pieper, jjp@pobox.com.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""
Make discrete position steps, write the results to a CSV file.
"""

import argparse
import asyncio
import csv
import math
import moteus
import time


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', '-o', default='data.csv',
                        help='Location to store output CSV file')
    args = parser.parse_args()

    output_file = open(args.output, "w")
    fieldnames = [
        'time',
        'desired_position',
        'position',
        'velocity',
        'torque',
        'mode',
        'fault',
    ]
    csv_writer = csv.DictWriter(output_file, fieldnames=fieldnames)
    csv_writer.writeheader()

    c = moteus.Controller()

    # Clear any faults that might remain from a previous run.
    await c.set_stop()

    # Remove any multi-turn offset so that the controller starts
    # between -0.5 and 0.5.
    await c.set_rezero()

    start_s = time.time()

    STEP_TIME_S = 2.0
    STEP_DIVISIONS = 6

    while True:
        now_s = time.time()
        offset_s = now_s - start_s

        # Stop after we have made one full revolution.
        if offset_s > STEP_TIME_S * (STEP_DIVISIONS + 1):
            await c.set_stop()
            print()
            break

        # This will result in a step function starting at 0, moving in
        # increments of 1.0 / STEP_DIVISONS.
        desired_position = math.floor(offset_s / STEP_TIME_S) / STEP_DIVISIONS

        # Send our current command, overriding the default
        # acceleration and velocity limits from the global
        # configuration.
        state = await c.set_position(position=desired_position,
                                     accel_limit=2.0,
                                     velocity_limit=5.0,
                                     query=True)

        position = state.values[moteus.Register.POSITION]
        velocity = state.values[moteus.Register.VELOCITY]
        torque = state.values[moteus.Register.TORQUE]
        mode = state.values[moteus.Register.MODE]
        fault = state.values[moteus.Register.FAULT]

        csv_writer.writerow({
            'time': offset_s,
            'desired_position': desired_position,
            'position': position,
            'velocity': velocity,
            'torque': torque,
            'mode': mode,
            'fault': fault,
        })

        # Just so we can see what is happening.
        print(f'{offset_s:0.2f} desired={desired_position:.03f} pos={position:.03f} vel={velocity:5.02f} torque={torque:5.02f}', end='\r')

        # Aim for about 100Hz operation.
        await asyncio.sleep(0.01)


if __name__ == '__main__':
    asyncio.run(main())

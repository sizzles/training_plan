from __future__ import absolute_import
import asyncio
import json
import io
import os
from training_plan import TrainingPlan

class TrainingPlanRepository:

        def __init__(self) -> None:
            self.save_folder:str = ''
            self.lock = asyncio.Lock()
            self.save_file_name = f'training_plan.json'

        async def save_plan(self, tp):
            async with self.lock:
                json_fmt = tp.to_json()
                
                save_file_path = os.path.join(self.save_folder, self.save_file_name)

                if not os.path.exists(save_file_path):
                    with io.open(save_file_path, 'x') as f:
                        f.write(json_fmt)
                else:
                    with io.open(save_file_path, 'w') as f:
                        f.write(json_fmt)

        async def load_plan(self): #todo upgrade to Python 3.10 to give union types
            save_file_path = os.path.join(self.save_folder, self.save_file_name)
            if os.path.exists(save_file_path):
                with io.open(save_file_path, 'r') as f:
                    json_fmt = json.load(f)
                    tp = TrainingPlan.from_json(json_fmt)
                    return tp
            else:
                return None
from __future__ import absolute_import

import sys

import pygame
import OpenGL.GL as gl

from imgui.integrations.pygame import PygameRenderer
import imgui
import imgui.core as core
import random
import pandas as pd
import datetime
import typing
import copy
import asyncio
import json
import io
import os

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

class TrainingPlan:
    
    def __init__(self, plan_name:str,start_date: datetime.date, end_date: datetime.date):
        self.plan_name = plan_name
        self.start_date = start_date
        self.end_date = end_date
        #Set the revised start dates - so the rendering is nicely in week blocks starting on Mondays
        #find the closest monday to the start_date
        #Monday = 1, Sunday = 7
        start_weekday_offset = self.start_date.isoweekday() -1
        end_weekday_offset = 7 - self.end_date.isoweekday()        
        #wind back to the previous monday
        self.revised_start_date = pd.to_datetime(self.start_date) - pd.DateOffset(days=start_weekday_offset)
        self.revised_end_date= pd.to_datetime(self.end_date) +  pd.DateOffset(days=end_weekday_offset) #fill out to the end monday

        print(self.revised_start_date)
        print(self.revised_end_date)

        column_names = ["Dates", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun", "WeeklyTotal"]
        self.df:pd.DataFrame = pd.DataFrame(columns=column_names)

        index = pd.date_range(start=self.revised_start_date, end=self.revised_end_date,freq='W-MON')

        self.df["Dates"] = index
        self.df.set_index(["Dates"],inplace=True)
        self.df.fillna(0, inplace=True)

        # for i in index:
        #     self.df[i] = list(map(lambda x: 0, column_names))
        #print(self.df)
    
    def update_start_end(self, new_start_date: datetime.date, new_end_date: datetime.date):
        
        self.start_date = new_start_date
        self.end_date = new_end_date

        #generate a new range
        start_weekday_offset = self.start_date.isoweekday() -1
        end_weekday_offset = 7 - self.end_date.isoweekday()    

        self.revised_start_date = pd.to_datetime(self.start_date) - pd.DateOffset(days=start_weekday_offset)
        self.revised_end_date= pd.to_datetime(self.end_date) +  pd.DateOffset(days=end_weekday_offset) #fill out to the end monday

        print(self.revised_start_date)
        print(self.revised_end_date)

        index = pd.date_range(start=self.revised_start_date, end=self.revised_end_date,freq='W-MON')

        self.df = self.df.reindex(index, fill_value = 0 )

    def get_plan_total_distance(self) -> int:
        return int(self.df.values.sum())

    def to_json(self):
        json_fmt = json.dumps({"plan_name": self.plan_name, "start_date": self.start_date, "end_date": self.end_date, "df": self.df.to_json()}, default=str)

        return json_fmt
    
    @classmethod
    def from_json(cls, json_fmt):
        plan_name = json_fmt["plan_name"]
        start_date_str = json_fmt["start_date"]
        end_date_str = json_fmt["end_date"]
        start_date =  datetime.datetime.strptime(str(start_date_str), '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(str(end_date_str), '%Y-%m-%d').date()

        df_str = json_fmt["df"]
        df = pd.read_json(df_str)


        # df = pd.read_json(json_fmt["df"])
        tp = TrainingPlan(plan_name=plan_name, start_date=start_date, end_date=end_date)
        tp.df = df   
        
        return tp

async def main():

    start_date = datetime.date(2021,12,15)
    end_date = datetime.date(2032,4,12)

    tp_repository = TrainingPlanRepository()

    tp = TrainingPlan("Default Training Plan", start_date, end_date)

    pygame.init()
    size = 1024, 768

    pygame.display.set_mode(size, pygame.DOUBLEBUF | pygame.OPENGL | pygame.RESIZABLE)

    imgui.create_context()
    impl = PygameRenderer()

    io = imgui.get_io()
    io.display_size = size

    height_val = str(768)

    days = list(range(1000))
    buffers = {}

    TARGET_FPS = '30'

    fpsClock = pygame.time.Clock()

    for d in days:
        buffers[d] = ''
    
    frame_elapsed_time = 0
    wait_budget = 0

    plan_buffers = {}

    start_date_valid = True
    end_date_valid = True    

    while 1:

        frame_start_time = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()

            impl.process_event(event)

        imgui.new_frame()
        
        if imgui.begin_main_menu_bar():
            if imgui.begin_menu("File", True):

                clicked_save, selected_save = imgui.menu_item(
                    "Save", 'Cmd+S', False, True
                )

                clicked_load, selected_load = imgui.menu_item(
                    "Load", "Cmd+O", False, True
                )

                clicked_quit, selected_quit = imgui.menu_item(
                    "Quit", 'Cmd+Q', False, True
                )

                if clicked_quit:
                    exit(1)

                if clicked_save:
                    await tp_repository.save_plan(tp)
                    #await   tp.save_plan('')

                if clicked_load:
                    temp = await tp_repository.load_plan()

                    if temp is not None:
                        tp = temp

                imgui.end_menu()
            imgui.end_main_menu_bar()


        imgui.show_test_window()

        imgui.begin("FPS Settings", True)
        imgui.push_item_width(30)
        imgui.text('Frame elapsed: ' + str(frame_elapsed_time))
        imgui.text('Wait budget: ' + str(wait_budget))
        _, TARGET_FPS = imgui.input_text('Target FPS: ', TARGET_FPS, 10)
        imgui.pop_item_width()
        imgui.end()

        imgui.begin(tp.plan_name, True)
        #imgui.begin_child("region", 850, -50, border=True)

        imgui.push_item_width(100)
        start_date_changed, start_date = imgui.input_text('Start Date', str(start_date), 11); imgui.same_line()
        imgui.next_column()
        end_date_changed, end_date = imgui.input_text('End Date', str(end_date), 11)

        if start_date_changed or end_date_changed:
            try:
                start_date = datetime.datetime.strptime(str(start_date), '%Y-%m-%d').date()#
                end_date = datetime.datetime.strptime(str(end_date), '%Y-%m-%d').date()#
                tp.update_start_end(start_date, end_date)
            except Exception as e:
                print("Error changing date")

        imgui.pop_item_width()

        columns = list(filter(lambda x : x not in ['WeeklyTotal'], tp.df.columns))
        dates = list(tp.df.index)

        imgui.columns(10)
       
        imgui.push_item_width(40)
        for c in  ['Week', 'Starting'] + columns + [f'Total: {str(tp.get_plan_total_distance())}']:
            imgui.text(str(c))#;imgui.same_line()
            imgui.next_column()
        
        #imgui.text(str(''))
        imgui.push_item_width(30)
        #imgui.input_text('', str(t), 10); imgui.same_line()
        imgui.pop_item_width()

        #week_num:int = 1
    
        for week_idx, d in enumerate(dates):
            
            #was the last item visible?


            week_num:int = week_idx + 1
            new_line = False

            #Render the date

            imgui.text(str(week_num))
            imgui.next_column()

            imgui.text(d.strftime('%Y-%m-%d'))#; imgui.same_line()
            weekly_total = 0

            for idx, c in enumerate(columns):
            

                imgui.next_column()
                is_last_col = idx == len(columns) -1

                core_id = str(d) + '_' + str(c)
                core.push_id(core_id)

                t = tp.df.loc[d, c]
                cell_changed = False

                # if is_last_col:
                #     cell_changed, buffers[core_id] = imgui.input_text('', str(t), 10)
                # else:

                if str(t) == '0':
                    cell_changed, buffers[core_id] = imgui.input_text('', '', 10)#; imgui.same_line()
                else:
                    cell_changed, buffers[core_id] = imgui.input_text('', str(t), 10)#; imgui.same_line()

                if cell_changed == True:
                    #Update the dataframe
                    if buffers[core_id] and str(buffers[core_id]).isdigit():
                        tp.df.at[d,c] = int(float(copy.copy(buffers[core_id])))

                if buffers[core_id] and str(buffers[core_id]).isdigit():
                    weekly_total += int(buffers[core_id])
          
                core.pop_id()
                new_line = False

            imgui.next_column()
            imgui.text(str(weekly_total))
            imgui.next_column()

            
        
        imgui.pop_item_width()


        #Cum sum total
        imgui.text(f'Total: {str(tp.get_plan_total_distance())}')
        imgui.next_column()
        #imgui.end_child()


        # for i in range(len(buffers.keys())):
        #     idx = 'buffers_' + str(i)
        #     r = random.randint(0,100)
        #     core.push_id(idx)
        #     imgui.text('Price: ' + str(r));imgui.same_line()
        #     _, buffers[i] = imgui.input_text('Day: ', str(buffers[i]), 10)
        #     core.pop_id()
            

            #buffers[i] = x
        
        #height_change, height_val = imgui.input_text('Height: ', height_val, 256)
        #imgui.text_colored("Eggs", 0.2, 1., 0.)

       

        imgui.end()

        first_run = False

        # note: cannot use screen.fill((1, 1, 1)) because pygame's screen
        #       does not support fill() on OpenGL sufraces
        gl.glClearColor(1, 1, 1, 1)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)


        

        imgui.render()
        impl.render(imgui.get_draw_data())

        pygame.display.flip()



        
        frame_elapsed_time = pygame.time.get_ticks() - frame_start_time
        
        #want 33 roughly for 30 fps
        #budget of what we can wait to hit that target
        target_fps_validated = 1

        if TARGET_FPS:
            target_fps_validated = int(max(1,min(int(TARGET_FPS), 120)))
        TARGET_FRAME_TIME = 1000/target_fps_validated#limit fps to 120
        wait_budget = max(int(TARGET_FRAME_TIME) - frame_elapsed_time, 0) #cant wait less than 0

        pygame.time.wait(wait_budget)
        

if __name__ == "__main__":
    asyncio.run(main())

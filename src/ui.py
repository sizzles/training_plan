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
from utils import check_if_current_week, check_if_today, get_default_start_end_date
from training_plan import TrainingPlan
from training_plan_repository import TrainingPlanRepository

class UI:
    def __init__(self) -> None:
        self.tp_repository = TrainingPlanRepository()
        self.today = datetime.datetime.now()
        self.start_date, self.end_date = get_default_start_end_date()

    def set_app_icon(self):
        icon_rect = pygame.Rect((0,0),(64,64))
        icon_image = pygame.image.load('./src/logo.png').convert()
        icon_surface = pygame.Surface((64,64))
        icon_surface.blit(icon_image, icon_rect)
        pygame.display.set_icon(icon_surface)

    def render_training_days_left(self, today:datetime.date, end_date):
        try:
            end_date = datetime.datetime.strptime(str(end_date), '%Y-%m-%d').date()
            days_remaining = (end_date - today).days

            descriptor = "day" if days_remaining == 1 else "days"

            imgui.text(f'- {days_remaining} {descriptor} left from today')
        except Exception as e:
            imgui.text('-')

    async def render_main_menu_bar(self):
        if imgui.begin_main_menu_bar():
            if imgui.begin_menu("File", True):
                clicked_new, selected_new = imgui.menu_item(
                    "New", 'Cmd+N', False, True
                )

                clicked_save, selected_save = imgui.menu_item(
                    "Save", 'Cmd+S', False, True
                )

                clicked_load, selected_load = imgui.menu_item(
                    "Load", "Cmd+O", False, True
                )

                clicked_quit, selected_quit = imgui.menu_item(
                    "Quit", 'Cmd+Q', False, True
                )

                if clicked_new:
                    self.tp = TrainingPlan.get_default_plan()
                    self.start_date = self.tp.start_date
                    self.end_date = self.tp.end_date  

                if clicked_save:
                    await self.tp_repository.save_plan(self.tp)

                if clicked_load:
                    temp = await self.tp_repository.load_plan()

                    if temp is not None:
                        self.tp = temp
                        self.start_date = self.tp.start_date
                        self.end_date = self.tp.end_date  
                if clicked_quit:
                    exit(1)

                imgui.end_menu()
            imgui.end_main_menu_bar()

    def render_plan_header(self):
        imgui.push_item_width(100)
        start_date_changed, self.start_date = imgui.input_text('Start Date', str(self.start_date), 11); imgui.same_line()
        end_date_changed, self.end_date = imgui.input_text('End Date', str(self.end_date), 11); imgui.same_line()
        self.render_training_days_left(today=self.today.date(), end_date=self.end_date)

        if start_date_changed or end_date_changed:
            try:
                self.start_date = datetime.datetime.strptime(str(self.start_date), '%Y-%m-%d').date()#
                self.end_date = datetime.datetime.strptime(str(self.end_date), '%Y-%m-%d').date()#
                self.tp.update_start_end(self.start_date, self.end_date)
                print('Changed start plan date')
            except Exception as e:
                print("Error changing date")

        imgui.pop_item_width()

    def render_week_start(self, week):
        is_current_week = check_if_current_week(self.today, week)
        if is_current_week:
            imgui.push_style_color(imgui.COLOR_TEXT, 0.0, 1.0, 0.0)
            imgui.text(week.strftime('%Y-%m-%d'))
            imgui.pop_style_color(1)
        else:
            imgui.text(week.strftime('%Y-%m-%d'))

    async def run(self):
        
        try:
            loaded_plan =  await self.tp_repository.load_plan()
            if loaded_plan is None:
                self.tp = TrainingPlan.get_default_plan()
            else:
                self.tp = loaded_plan
                self.start_date = self.tp.start_date
                self.end_date = self.tp.end_date
        except Exception as e:
            self.tp = TrainingPlan.get_default_plan()

        pygame.init()
        size = 1024, 768

        pygame.display.set_mode(size, pygame.DOUBLEBUF | pygame.OPENGL | pygame.NOFRAME )

        self.set_app_icon()

        imgui.create_context()
        impl = PygameRenderer()

        io = imgui.get_io()
        io.display_size = size
        buffers = {}

        TARGET_FPS = '30'

        frame_elapsed_time = 0
        wait_budget = 0
        while 1:
            today = datetime.datetime.now()
            frame_start_time = pygame.time.get_ticks()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    sys.exit()

                impl.process_event(event)

            imgui.new_frame()
            
            await self.render_main_menu_bar()

            #FPS Settings Window
            imgui.set_next_window_size(1024, 55)
            imgui.set_next_window_position(0, 715)
            imgui.begin("FPS Settings", True, flags=imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_COLLAPSE | imgui.WINDOW_NO_MOVE)
            imgui.columns(3)
            #imgui.push_item_width(30)
            imgui.text('Frame elapsed: ' + str(frame_elapsed_time))
            imgui.next_column()
            imgui.text('Wait budget: ' + str(wait_budget))
            imgui.next_column()
            _, TARGET_FPS = imgui.input_text('Target FPS: ', TARGET_FPS, 10)
            #imgui.pop_item_width()
            imgui.end()

            #Main Training Plan Window
            imgui.set_next_window_size(1024, 698)
            imgui.set_next_window_position(0, 18)
            imgui.begin(self.tp.plan_name, True, flags=imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_COLLAPSE | imgui.WINDOW_NO_MOVE)
            
            self.render_plan_header()

            columns = list(filter(lambda x : x not in ['WeeklyTotal'], self.tp.df.columns))
            weeks = list(self.tp.df.index)

            imgui.columns(10)
        
            imgui.push_item_width(40)
            for c in  ['Week', 'Starting'] + columns + [f'Total: {str(self.tp.get_plan_total_distance())}']:
                imgui.text(str(c))
                imgui.next_column()
        
            for week_idx, week in enumerate(weeks):                
                week_num:int = week_idx + 1

                #Render Week Number
                imgui.text(str(week_num))

                if core.is_item_visible() == False:
                    for i in range(10):
                        imgui.next_column()
                    continue

                imgui.next_column()

                self.render_week_start(week)

                weekly_total = 0

                for idx, c in enumerate(columns):
                    imgui.next_column()

                    cell_id = str(week) + '_' + str(c)
                    core.push_id(cell_id)

                    t = self.tp.df.loc[week, c]
                    cell_changed:bool = False

                    cell_value = '' if str(t) == '0' else str(t)

                    is_today = check_if_today(self.today, week, idx)
                    if is_today:
                        imgui.push_style_color(imgui.COLOR_TEXT, 0.0, 1.0, 0.0)
                        cell_changed, buffers[cell_id] = imgui.input_text('', cell_value, 10)#; imgui.same_line()
                        imgui.pop_style_color(1)
                    else:
                        cell_changed, buffers[cell_id] = imgui.input_text('', cell_value, 10)#; imgui.same_line()
                    
                    if cell_changed == True:
                        #Update the dataframe
                        if buffers[cell_id] and str(buffers[cell_id]).isdigit():
                            self.tp.df.at[week,c] = int(float(copy.copy(buffers[cell_id])))
                    
                    if buffers[cell_id] and str(buffers[cell_id]).isdigit():
                        weekly_total += int(buffers[cell_id])
            
                    core.pop_id()

                imgui.next_column()
                imgui.text(str(weekly_total),)
                imgui.next_column()

                
            
            imgui.pop_item_width()


            #Cum sum total
            imgui.text(f'Total: {str(self.tp.get_plan_total_distance())}')
            imgui.next_column()
            #imgui.end_child()      

            imgui.end()

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

            if pygame.display.get_active() == False:
                target_fps_validated = 2
            else:
                if TARGET_FPS:
                    target_fps_validated = int(max(1,min(int(TARGET_FPS), 120)))
            TARGET_FRAME_TIME = 1000/target_fps_validated#limit fps to 120

            wait_budget = max(int(TARGET_FRAME_TIME) - frame_elapsed_time, 0) #cant wait less than 0
            pygame.time.wait(wait_budget)
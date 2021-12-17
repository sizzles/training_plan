from __future__ import absolute_import
import sys
import OpenGL.GL as gl
from imgui.integrations.pygame import PygameRenderer
import imgui.core as core
import pandas as pd
import datetime
import json
import typing
from utils import get_default_start_end_date


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
    def get_default_plan(cls):
        default_start_date, default_end_date = get_default_start_end_date()
        tp = TrainingPlan("Training Plan", default_start_date, default_end_date)
        return tp

    @classmethod
    def from_json(cls, json_fmt):
        plan_name = json_fmt["plan_name"]
        start_date_str = json_fmt["start_date"]
        end_date_str = json_fmt["end_date"]
        start_date =  datetime.datetime.strptime(str(start_date_str), '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(str(end_date_str), '%Y-%m-%d').date()

        df_str = json_fmt["df"]
        df = pd.read_json(df_str)

        tp = TrainingPlan(plan_name=plan_name, start_date=start_date, end_date=end_date)
        tp.df = df   
        
        return tp
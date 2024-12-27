import streamlit as st
import requests
from datetime import datetime, timedelta, time
import calendar
import json
import pandas as pd

class ResyAPI:
    def __init__(self):
        self.base_url = "https://api.resy.com/4"
        self.headers = {
            'authorization': 'ResyAPI api_key="VbWk7s3L4KiK5fzlO7JD3Q5EYolJI7n5"',
            'origin': 'https://resy.com',
            'referer': 'https://resy.com/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        }
        
        self.restaurants = {
            'FIG': 551,
            'SHIKI': 8038,
            "VERN'S": 60323,
            'CHEZ NOUS': 753,
            'SORGHUM & SALT': 998,
            'HONEYSUCKLE ROSE': 77435,
            'CIRCA 1866': 7382,
            'ZERO GEORGE': 5672
        }

    def get_venue_calendar(self, venue_id: int, num_seats: int, days_ahead: int = 30) -> dict:
        start_date = datetime.now().strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        
        url = f"{self.base_url}/venue/calendar"
        params = {
            'venue_id': venue_id,
            'num_seats': num_seats,
            'start_date': start_date,
            'end_date': end_date
        }

        response = requests.get(url, headers=self.headers, params=params)
        return response.json()

    def get_available_times(self, venue_id: int, date: str, party_size: int) -> dict:
        url = f"{self.base_url}/find"
        params = {
            'lat': 0,
            'long': 0,
            'day': date,
            'party_size': party_size,
            'venue_id': venue_id
        }

        response = requests.get(url, headers=self.headers, params=params)
        return response.json()

    def is_within_time_range(self, time_str: str, start_time: time, end_time: time) -> bool:
        time_obj = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S").time()
        return start_time <= time_obj <= end_time

    def get_availability_data(self, party_size: int, start_time: time, end_time: time):
        all_availability = {}
        
        for restaurant_name, venue_id in self.restaurants.items():
            restaurant_data = {
                'available_dates': set(),
                'time_slots': {}
            }
            
            try:
                # Get calendar data
                calendar_data = self.get_venue_calendar(venue_id, party_size)
                
                # Find available days
                for day in calendar_data.get('scheduled', []):
                    if day['inventory'].get('reservation') == 'available':
                        date = day['date']
                        
                        # Get time slots for available days
                        time_data = self.get_available_times(venue_id, date, party_size)
                        slots = time_data.get('results', {}).get('venues', [{}])[0].get('slots', [])
                        
                        # Filter for times within range
                        filtered_slots = [
                            slot for slot in slots 
                            if self.is_within_time_range(slot['date']['start'], start_time, end_time)
                        ]
                        
                        if filtered_slots:
                            restaurant_data['available_dates'].add(date)
                            restaurant_data['time_slots'][date] = [
                                {
                                    'time': datetime.strptime(slot['date']['start'], "%Y-%m-%d %H:%M:%S").strftime("%I:%M %p"),
                                    'type': slot['config']['type']
                                }
                                for slot in filtered_slots
                            ]
                
                if restaurant_data['available_dates']:
                    all_availability[restaurant_name] = restaurant_data
                    
            except Exception as e:
                st.error(f"Error checking {restaurant_name}: {e}")
                
        return all_availability

def create_time_filter():
    st.sidebar.markdown("### Time Range Filter")
    col1, col2 = st.sidebar.columns(2)
    
    # Default times (5:30 PM - 7:00 PM)
    default_start = time(17, 30)  # 5:30 PM
    default_end = time(19, 0)    # 7:00 PM
    
    with col1:
        start_hour = st.number_input("Start Hour", min_value=11, max_value=23, value=default_start.hour)
        start_minute = st.selectbox("Start Minute", [0, 15, 30, 45], index=2)  # Default to 30
    
    with col2:
        end_hour = st.number_input("End Hour", min_value=11, max_value=23, value=default_end.hour)
        end_minute = st.selectbox("End Minute", [0, 15, 30, 45], index=0)  # Default to 0
    
    start_time = time(start_hour, start_minute)
    end_time = time(end_hour, end_minute)
    
    return start_time, end_time

def create_calendar_view(availability_data):
    # Get current date and calculate next 30 days
    today = datetime.now()
    dates = [today + timedelta(days=x) for x in range(30)]
    
    # Create CSS for the calendar
    st.markdown("""
        <style>
        .calendar-day {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: center;
        }
        .time-chip {
            display: flex;
            flex-direction: column;
            padding: 4px 10px;
            margin: 4px 0;
            border-radius: 8px;
            font-size: 12px;
            background-color: #4CAF50;
            color: white;
            width: fit-content;
        }
        .time-slot {
            font-weight: bold;
            margin-bottom: 2px;
        }
        .seating-type {
            font-size: 10px;
            opacity: 0.9;
        }
        .restaurant-name {
            font-weight: bold;
            margin-top: 4px;
            margin-bottom: 2px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Group dates by week
    weeks = []
    current_week = []
    
    for date in dates:
        if current_week and current_week[-1].weekday() == 6:
            weeks.append(current_week)
            current_week = []
        current_week.append(date)
    if current_week:
        weeks.append(current_week)
    
    # Display each week
    for week in weeks:
        cols = st.columns(7)
        for i, date in enumerate(week):
            with cols[i]:
                date_str = date.strftime("%Y-%m-%d")
                st.markdown(f"### {date.strftime('%d')}")
                st.markdown(f"*{date.strftime('%a')}*")
                
                # Display restaurant availability
                for restaurant, data in availability_data.items():
                    if date_str in data['available_dates']:
                        with st.expander(restaurant):
                            for slot in data['time_slots'][date_str]:
                                st.markdown(
                                    f"""<div class='time-chip'>
                                        <div class='time-slot'>{slot['time']}</div>
                                        <div class='seating-type'>{slot['type']}</div>
                                    </div>""",
                                    unsafe_allow_html=True
                                )

def main():
    st.set_page_config(page_title="Charleston Restaurant Availability", layout="wide")
    st.title("Charleston Restaurant Availability")
    
    # Sidebar controls
    party_size = st.sidebar.number_input("Party Size", min_value=1, max_value=8, value=2)
    
    # Time range filter
    start_time, end_time = create_time_filter()
    
    # Initialize ResyAPI
    resy = ResyAPI()
    
    # Get availability data
    with st.spinner("Checking availability..."):
        availability_data = resy.get_availability_data(party_size, start_time, end_time)
    
    # Display calendar view
    if availability_data:
        create_calendar_view(availability_data)
    else:
        st.info(f"No availability found between {start_time.strftime('%I:%M %p')} and {end_time.strftime('%I:%M %p')} for the next 30 days.")

if __name__ == "__main__":
    main()
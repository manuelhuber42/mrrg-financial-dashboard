# --- 2. THE SCHEDULE ENGINE (Daily Math per Car) ---
# 1. Total theoretical distance if driving non-stop
max_theoretical_km = active_hours_per_day * avg_speed_kmh
theoretical_deadhead_km = max_theoretical_km * deadhead_rate
max_billable_km_theoretical = max_theoretical_km - theoretical_deadhead_km

# 2. Dwell Penalty (Distance lost while passengers get in/out)
distance_lost_per_dwell_km = (avg_speed_kmh / 60) * dwell_time_mins
effective_trip_distance_km = avg_trip_distance_km + distance_lost_per_dwell_km

# 3. Total Trips & Actual Billable Distance
actual_trips_per_day = np.floor(max_billable_km_theoretical / effective_trip_distance_km)
actual_billable_km_per_day = actual_trips_per_day * avg_trip_distance_km

# 4. FIXED: Actual Total KM (Maintaining the strict 30% deadhead ratio)
# If billable km is 70% of the day, total km is Billable / 0.70
actual_total_km_per_day = actual_billable_km_per_day / (1 - deadhead_rate)
actual_deadhead_km = actual_total_km_per_day - actual_billable_km_per_day

# 5. Daily Revenue Math (per car)
base_fare_rev_per_day = actual_trips_per_day * base_fare_eur
distance_rev_per_day = actual_billable_km_per_day * price_per_km_eur
gross_revenue_per_day_per_car = base_fare_rev_per_day + distance_rev_per_day

# 6. Annual Fleet Topline
operating_days = 365
annual_gross_revenue_fleet = gross_revenue_per_day_per_car * operating_days * fleet_size
annual_tesla_fees = annual_gross_revenue_fleet * tesla_take_rate
annual_net_revenue = annual_gross_revenue_fleet - annual_tesla_fees

# Pollutions for minute spent in transportation mode (grams of CO2 / minute)
POLLUTION_COEFFICIENTS = {
    "walking": 0,
    "bicycling": 0,
    "transit": 0.9,
    "driving": 3.75
}

BASELINE_POLLUTION_FACTOR = 3.75


class PollutionCalculator:
    def calculate(self, stages_travel_times):
        total_emission = 0
        total_saved_co2 = 0
        total_saved_trees = 0
        total_time = 0
        total_efficiency = 0

        for mean,time in stages_travel_times.items():
            car_pollution_penalty = 0
            if (mean == "driving") and (time > 0):
                car_pollution_penalty = 240 / time

            emission = time * POLLUTION_COEFFICIENTS[mean]
            saved_co2 = time * BASELINE_POLLUTION_FACTOR - emission
            saved_trees = saved_co2 / 54.8
            efficiency = 1000 / (emission + (2 * time ** 1.2) + car_pollution_penalty + 1)

            total_emission += emission
            total_saved_co2 += saved_co2
            total_saved_trees += saved_trees
            total_time += time
            total_efficiency += efficiency

        return {
            "emission": total_emission,
            "saved_co2": total_saved_co2,
            "saved_trees": total_saved_trees,
            "time": total_time,
            "efficiency": total_efficiency
        }







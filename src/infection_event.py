"""
InfectionEvent class defition script for object-oriented instancing of infection predictions.

"""

import infection_model


class InfectionEvent:
    """
    Class InfectionEvent to compute and print out individual instances
    of infection predictions at different datetimes across the input timeseries.

    """

    def __init__(
        self,
        timeseries,
        parameters,
        start_event_rowindex,
        oospore_maturation_date,
        daily_mean_temperatures,
        algorithmic_time_steps,
        logfile,
        oospore_infection_datetimes,
    ):
        """
        Object initialisation function.

        """
        self.timeseries = timeseries
        self.parameters = parameters
        self.start_event_rowindex = start_event_rowindex
        self.oospore_maturation_date = oospore_maturation_date
        self.daily_mean_temperatures = daily_mean_temperatures
        self.algorithmic_time_steps = algorithmic_time_steps
        self.logfile = logfile
        self.oospore_infection_datetimes = oospore_infection_datetimes
        self.start_event_datetime = timeseries["datetime"][self.start_event_rowindex]
        self.id = start_event_rowindex

    def predict_infection(self):
        """
        Infection prediction calling-function.

        """
        self.infection_events = infection_model.run_infection_model(
            self.timeseries,
            self.parameters,
            self.start_event_rowindex,
            self.oospore_maturation_date,
            self.daily_mean_temperatures,
            self.algorithmic_time_steps,
            self.logfile,
            self.oospore_infection_datetimes,
        )

    def __str__(self):
        """
        Object printing function.

        """
        return f"{self.id}: START:{self.start_event_datetime}: EVENTS:{self.infection_events}"

"""
Spore die-off counting algorithms.

"""

from math import exp, log


def get_saturation_deficit(saturation_vapor_pressure, humidity, temperature):
    """
    Formula to compute the saturation deficit required for the calculation of the spore lifespan.

    """

    saturation_deficit = None

    if saturation_vapor_pressure is None:
        saturation_vapor_pressure = 6.1 * exp(7.5 * temperature / (235 + temperature))

    # Saturation deficit according to MAGNUS formula from Quantit. Hydrology, Baumgartner, 1996
    saturation_deficit = saturation_vapor_pressure * (1 - humidity / 100)

    return saturation_deficit


def get_spore_lifespan(saturation_deficit, spore_lifespan_constant):
    """
    Formula to compute the spore lifespan in days from saturation deficit values.

    """

    # Limiting the saturation deficit value to 0.1, below that we force the formula
    # to converge to the minimal value corresponding to the solution with saturation_deficit = 0.1
    saturation_deficit = max(saturation_deficit, 0.1)

    spore_lifespan_days = (
        -2.529553487 * log(saturation_deficit) + spore_lifespan_constant
    )

    return spore_lifespan_days


def launch_spore_lifespans(
    processed_data,
    saturation_vapor_pressure,
    spore_lifespan_constant,
    sporulation_datetime_rowindexes,
):
    """
    Formula to launch spore lifespan computations for all sporangia density counts.

    """

    # spore_lifespan_days = {}
    #
    # for sporulation_datetime_rowindex, _count in sporangia_counts.items():
    #     humidity = processed_data["humidity"][sporulation_datetime_rowindex]
    #     temperature = processed_data["temperature"][sporulation_datetime_rowindex]
    #
    #     saturation_deficit = get_saturation_deficit(
    #         saturation_vapor_pressure, humidity, temperature
    #     )
    #     spore_lifespan = get_spore_lifespan(saturation_deficit, spore_lifespan_constant)
    #
    #     if sporulation_datetime_rowindex not in spore_lifespan_days.keys():
    #         spore_lifespan_days[sporulation_datetime_rowindex] = [spore_lifespan]
    #     else:
    #         spore_lifespan_days[sporulation_datetime_rowindex].append(spore_lifespan)

    spore_lifespan_days = []

    for sporulation_datetime_rowindex in sporulation_datetime_rowindexes:
        humidity = processed_data["humidity"][sporulation_datetime_rowindex]
        temperature = processed_data["temperature"][sporulation_datetime_rowindex]

        saturation_deficit = get_saturation_deficit(
            saturation_vapor_pressure, humidity, temperature
        )
        spore_lifespan = get_spore_lifespan(saturation_deficit, spore_lifespan_constant)

        spore_lifespan_days.append(spore_lifespan)

        # if sporulation_datetime_rowindex not in spore_lifespan_days.keys():
        #     spore_lifespan_days[sporulation_datetime_rowindex] = [spore_lifespan]
        # else:
        #     spore_lifespan_days[sporulation_datetime_rowindex].append(spore_lifespan)

    return spore_lifespan_days

# Plasmopy v1.0
## Manual


### Input data - Weather variables

Input data needs to be in the form of timeseries, where the positioning of columns must be precisely kept in the following order:

1. Date and time of measurement in the *%d.%m.%Y %H:%M* local timezone format.

2. Average temperature *[°C]* in degrees Celsius.

3. Relative humidity *[%]* in percentages.

4. Rainfall intensity *[mm/h]* in millimeters per hour.

5. Leaf wetness *[min]* in minutes of wetness over 10 minutes.

### Optional input data - Spore counts

Input spore counts data (e.g. from qPCR, microscopy, ...) columns must be ordered and formatted in the following way:

1. Date of daily spore counts in the *%d.%m.%Y %H:%M* local timezone format.

2. Spore counts.

### Infection algorithms

#### 1. Oospore maturation

If oospore maturation date not observed in the field thus cannot be manually inserted, then compute it with the following formula [Gehmann 1991]:

<div align="center">

For **_day = i_** , where **_i = [FirstDay, LastDay]_**;

FirstDay and LastDay represent the first and last days indexed in the full meterological dataset provided as input.

_SumDegreeDays<sub>0</sub> = 0_

If:

_DailyAverageTemperature<sub>i</sub> > MaturationBaseTemperature_

Then:

_SumDegreeDays<sub>i</sub> = SumDegreeDays<sub>i-1</sub> + (DailyAverageTemperature<sub>i</sub> - MaturationBaseTemperature)_

Otherwise:

_SumDegreeDays<sub>i</sub> = SumDegreeDays<sub>i-1</sub>_

For each day **_i_**, if:

_SumDegreeDays<sub>i</sub> >= MaturationThreshold_ , then: _**OosporeMaturationDate = i**_
</div>


#### 2. Oospore germination

Stage 1 of primary infection, i.e. oospore infection from soil. This stage can be run by either one of two algorithms:

**Algorithm 1, oospore development**:

<div align="center">

Starting from OosporeMaturationDate at 00:00 (i.e. OosporeMaturationDatetime):

For **_datetime = j_** , where **_j = [OosporeMaturationDatetime, LastDatetime]_**

If:

_Temperature<sub>j</sub> > OosporeGerminationBaseTemperature_

And either:

_RelativeHumidity<sub>j</sub> > OosporeGerminationRelativeHumidityThreshold_

Or:

_LeafWetness<sub>j</sub> >= OosporeGerminationLeafWetnessThreshold_

For each **_j_** continuously during a total period of **_OosporeGerminationBaseDuration_**, then:

**_OosporeGerminationDatetime = j + OosporeGerminationBaseDuration_**

</div>


If no datetime could be found due to never reaching the conditions, then the oospore germination datetime can not be found and the model is interrupted for the whole season.


**Algorithm 2, moisture penetration**:

Starting from OosporeMaturationDate at 00:00 (i.e. OosporeMaturationDatetime):

<div align="center">

For **_datetime = j_** , where **_j = [OosporeMaturationDatetime, LastDatetime]_**

_CumulativePrecipitation<sub>0</sub> = 0_

If:

_Temperature<sub>j</sub> > MoisturizationTemperatureThreshold_

Then:

_CumulativePrecipitation<sub>j</sub> = CumulativePrecipitation<sub>j-1</sub> + Rainfall<sub>j</sub>_

Subsequently, if:

_CumulativePrecipitation<sub>j</sub> >= MoisturizationRainfallThreshold_

And:





MoisturizationRainfallPeriod

</div>

#### 3. Oospore dispersion

Stage 2 of primary infection, i.e. oospore spreading through rain splashing.

#### 4. Oospore infection

Stage 3 of primary infection, i.e. activating conditions for a successful oospore infection.

#### 5. Incubation

#### 6. Sporulation

#### 7. Estimation of sporangia density

#### 8. Estimation of spore life-span

#### 9. Secondary infection

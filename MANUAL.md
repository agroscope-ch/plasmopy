# Plasmopy v1.0
## Manual


### Input data - Weather variables

Input data needs to be in the form of timeseries in a semicolon-delimited CSV file, where the positioning of columns must be precisely kept in the following order:

1. Date and time of measurement in the *%d.%m.%Y %H:%M* local timezone format.

2. Average temperature *[°C]* in degrees Celsius.

3. Relative humidity *[%]* in percentages.

4. Rainfall intensity *[mm/h]* in millimeters per hour.

5. Leaf wetness *[min]* in minutes of wetness over 10 minutes.

Such timeseries data is publicly available for Switzerland from the Agroscope weather stations, accessible at [Agrometeo](https://www.agrometeo.ch/meteorologie).

### Optional input data - Spore counts

Input spore counts data (e.g. from qPCR, microscopy, ...) columns must be ordered and formatted in the following way:

1. Date of daily spore counts in the *%d.%m.%Y %H:%M* local timezone format.

2. Spore counts.

### Infection algorithms

#### 1. Oospore maturation

If oospore maturation date not observed in the field thus cannot be manually inserted, then compute it with the following formula [Gehmann 1991]:

<div align="center">

</div>


#### 2. Oospore germination

Stage 1 of primary infection, i.e. oospore infection from soil. This stage can be run by either one of two algorithms:

**Algorithm 1, oospore development**:

<div align="center">


</div>


If no datetime could be found due to never reaching the conditions, then the oospore germination datetime can not be found and the model is interrupted for the whole season.


**Algorithm 2, moisture penetration**:


<div align="center">


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

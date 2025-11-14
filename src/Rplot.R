library(plotly)
library(lubridate)


filepath <- "../data/output/2025_meteo_changins/2025_meteo_changins.events_dataframe.csv"
df <- read.csv2(filepath, sep = ",", na.strings = "None")

tz <- "Europe/Zurich"

df$start <- as_datetime(df$start, tz = tz)
df$oospore_maturation <- as_datetime(df$oospore_maturation, tz = tz)
df$oospore_germination <- as_datetime(df$oospore_germination, tz = tz)
df$oospore_dispersion <- as_datetime(df$oospore_dispersion, tz = tz)
df$oospore_infection <- as_datetime(df$oospore_infection, tz = tz)
df$completed_incubation <- as_datetime(df$completed_incubation, tz = tz)
df$sporulations <- as_datetime(df$sporulations, tz = tz)
df$secondary_infections <- as_datetime(df$secondary_infections, tz = tz)

xstart <- df$start[1]
xend <- max(df$secondary_infections, df$oospore_germination, df$start,
            df$oospore_dispersion, df$oospore_infection, df$completed_incubation,
            df$sporulations, na.rm = T)

ymin <- 0
ymax <- 325000

sporangia_densities <- df$sporangia_densities[!is.na(df$sporangia_densities)]
sporulations_datetimes <- df$sporulations[!is.na(df$sporangia_densities)]

plot(sporulations_datetimes, sporangia_densities, xlim = c(xstart, xend),
     type = "h", col = "darkblue", ylim = c(ymin, ymax), lwd = 2, xaxt = "n",
     yaxt = "n", xlab = "",
     ylab = expression('Leaf sporangia density [sporangia / cm'^{2}~']'))
title("Changins 2025")
axis(2, cex.axis = 1)
xticks <- as_datetime(seq(xstart, xend, by = "weeks"))
axis(1, at = xticks, format(xticks, "%b %d"), cex.axis = 1, las = 2)

points(df$oospore_maturation[1], 0, col = "darkgreen", pch = 15, cex = 1.5)

for (i in 1:nrow(df)) {
  xvalues <- c(df$oospore_germination[i], df$oospore_dispersion[i],
               df$oospore_infection[i], df$completed_incubation[i],
               df$sporulations[i], df$secondary_infections[i])
  yvalues <- c(0, 0.75e5, 1.5e5, 2.25e5, 3e5, 3.25e5)
  lines(xvalues, yvalues, type = "o", pch = c(1,2,3,4,25,5), lwd = 0.5, lty = 3)
}

legend("topleft", legend = rev(c("maturation", "germination", "dispersion",
                             "primary infection", "completed incubation",
                             "sporulation", "secondary infection")), cex = 0.7,
       bg = NA, box.lwd = 0, pch = rev(c(15,1,2,3,4,25,5)), col = rev(c("darkgreen", rep("black",6))))

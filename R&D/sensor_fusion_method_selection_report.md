# Sensor Fusion Method Selection Report

## Overview

### Problem
We have a lot of sensors, but each one logs data at different times and with some error associated with it. Based on the GPS and other sensors, we have to infer position at a consistent timing interval. In doing this, we have to predict the values for the sensors, so that down the pipeline we can also extract some metrics from those if we want.

### Our Data
We have a large amount of data. However, our sensors tend to have inconsistent levels of error, and the testing conditions are not constant, since the track and GPS location change between runs.

### Models Considered
Bayesian inference models are models that update predictions based on gaining more knowledge. The ones we looked into include the Kalman filter (KF), its cousin the unscented Kalman Filter (UKF), unscented Rauch–Tung–Striebel (RTS) smoother, and splines.

We also considered ML models. These need training data, which could be generated since we have a plethora of data, but they might overfit to certain situations and aren't as versatile for live use or for irregular trends, which is likely given our sensors. None of the basic ML models will really work well here. A random forest might be worth considering, but it probably isn't well suited to predicting from purely numerical columns, so a specialized approach would be needed.

From [research](https://medium.com/@wilburdes/sensor-fusion-algorithms-for-autonomous-driving-part-1-the-kalman-filter-and-extended-kalman-a4eab8a833dd) into the vehicle and robotics industries, Kalman filtering and its variants, including EKF and [UKF](https://pmc.ncbi.nlm.nih.gov/articles/PMC7249166/), are consistently used as the standard approach for vehicle state estimation and sensor fusion. [ML](https://pmc.ncbi.nlm.nih.gov/articles/PMC5038678/) can be integrated directly into the filter, most often to replace or assist the noise and parameter estimation the filter relies on, addressing the inconsistent sensor error we are dealing with. This kind of integration is a reasonable direction for future work, but is likely overkill for our current scope.

### Final Recommendation
**UKF combined with URTS (Unscented RTS smoothing).**

## Reasoning

### Bayesian Models vs. ML Models
Bayesian models predict based on the data they have seen so far, combined with a model of how the system is expected to behave. In our case, that expected behavior comes from physics equations describing the car's motion, such as constant velocity or constant turn rate. Rather than fitting a curve shape purely from the pattern of past data, the model uses the physics equations to generate a prediction, then updates that prediction using the marginal likelihood. The marginal likelihood is the probability that a given sensor reading would look the way it does if the prediction were correct. Predictions that make the sensor readings more probable are weighted more heavily than ones that do not.

Since this process relies on the physics model and the sensor data already collected, in our case the readings from a single lap, no separate training set is needed the way it would be for an ML model. Since we are not tracking metrics live, we can also use data points that come after a given moment to refine our prediction at that moment.

ML models use only the training set to predict all test sets, meaning all future data. Since our data does not follow a reliable pattern, ML is probably not the best option unless we use something that can heavily account for error, and we are not yet sure what that would be. ML models are usually good for large amounts of data, but only if we can trust that the training data accurately reflects the testing conditions, which may not hold for a track the car only drives once, or for a bad run.

### Bayesian Model Types

#### Kalman Filtering
Kalman filtering takes our prediction about the state (speed, position, and other variables linked together via physics equations) along with any sensor readings, and uses them to update the final state prediction. The weighting between trusting our predictive model of state (the physics) versus the actual sensor readings that update the state depends on two things: how long ago the last state update was from a sensor reading, and the error on the sensor reading itself. This weighting is calculated using the Kalman gain formula, which ranges from 0 to 1. The filter only looks at data before the time we are trying to predict.

Kalman filtering is not well suited to data with inconsistent error, since it will shift trends dramatically toward errors that seem unreasonable given the prediction. It can also only model linear relationships between states, which is not always representative of what our car does. The usual physics equations used are constant velocity (CV), which is best for cars moving at a constant speed and direction, and constant acceleration (CA), which can account for changes in speed. Neither of these accounts for angular motion.

#### UKF
UKF is a version of KF that performs a few more calculations per pass, resulting in a slight performance trade-off. It takes 2N + 1 other possible state points within the range of error for the state, where the range of error is determined by how long ago the last sensor reading was, since a longer gap means more uncertainty in the prediction, as it is based purely on the ideal physics model. N is the number of variables in the state. It then calculates the predicted next state for all of the sigma points and produces a predicted value with uncertainty. This predicted value is what gets blended, via the Kalman gain, with the actual updated state from the sensors, and the result becomes the new last state point.

The main difference from KF is that UKF can account for nonlinear motion, allowing it to more accurately predict turns without needing constant sensor correction, since KF can only model linear relationships between states, which does not always reflect what our car does. The main physics equations used with UKF include constant turn rate and velocity (CTRV), which works well if the car is not changing speeds suddenly and is more computationally efficient due to having fewer state variables, and constant turn rate and acceleration (CTRA), which works well if the car changes speeds suddenly but comes with a higher computational cost. We should most likely use CTRA, since it is expected that our car will be changing speeds suddenly and taking turns. More complex models can be used in industry, but we feel that CTRA is a good starting point without as much computational trade-off.

#### Unscented RTS
Unscented RTS follows the same basic idea as UKF, but uses all of the data available, both past and future, relative to the point we are trying to predict. After a lap's data has been recorded, including our predictions and the sensor readings, this method looks back over all of the data and corrects prediction points in the same way UKF does, only using future data instead of past data. This would increase computation, resulting in performance impacts, but for a more reliable predictive model which could be useful since our sensors are noisy.

#### Splines
Instead of relying on physics equations and probability, a smoothing spline fits a smooth curve through each sensor's data points, and each point can be weighted by how much we trust it or its sensor. Noisy or uncertain sensor readings get less influence, while more confident sensor readings pull the curve harder.

There are several drawbacks to this approach. It sacrifices accuracy since it has no estimate of what the physical positions are supposed to be, most of our sensors are noisy so it is not clear which ones we would weigh more heavily, and our sensor values cannot correlate with each other during prediction. The only advantage is that it is much easier to implement.

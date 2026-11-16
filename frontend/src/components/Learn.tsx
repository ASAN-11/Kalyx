type Sec = { title: string; body: string[] };
const SECTIONS: Sec[] = [
  { title: "What is a trend, and what is a trend test?", body: [
    "A trend is a long-term tendency for a variable to rise or fall. A line on a graph can slope up or down just by chance, because natural records vary from year to year. A trend test asks a narrower question: if there were really no trend, how surprising would data like this be?",
    "KALYX reports two things for every investigation: how large the change is (the slope, in units per decade) and how strong the evidence is (the p-value). Both matter. A tiny change can be statistically significant in a long record, and a large change can fail to reach significance in a short, noisy one." ] },
  { title: "Reading the verdict", body: [
    "“Significant increasing/decreasing trend” means the p-value is below your chosen significance level (0.05 by default), so a no-trend explanation is unlikely under the test's assumptions.",
    "“Increasing/decreasing but not statistically significant” means the data lean one way but the evidence is not strong enough. It does not mean nothing is changing; the record may be too short or too noisy to tell.",
    "“Insufficient data” appears when fewer than 60 monthly values remain. Short records give unreliable trend estimates, so KALYX declines to give a verdict." ] },
  { title: "The four trend numbers", body: [
    "Linear regression (OLS) fits a straight line and reports its slope with a 95% confidence interval. It is easy to interpret but sensitive to outliers.",
    "Sen's slope is the median of the slopes between every pair of points. It is robust to outliers and does not assume a straight line fits perfectly.",
    "The Mann-Kendall test counts, over every pair of observations, whether the later value is higher or lower than the earlier one. If one direction dominates, there is a monotonic trend. It needs no assumption that the data are normally distributed, which is why it is widely used in hydrology and climate science.",
    "The seasonal Mann-Kendall test (Hirsch) does that comparison separately within each calendar month and combines the results, so the yearly cycle can neither create nor hide a trend." ] },
  { title: "Why seasonality matters", body: [
    "Temperature, rainfall and vegetation follow a yearly cycle that is far larger than any slow trend. Mixing all months together can make a test confuse the cycle with change, especially when a record starts or ends mid-year or has missing months.",
    "KALYX can remove the seasonal cycle by subtracting each calendar month's long-term average, leaving anomalies. It can also use the seasonal Mann-Kendall test, which compares like with like. For monsoon regions such as eastern India, where wet and dry months differ enormously, one of these is strongly recommended." ] },
  { title: "Autocorrelation: why consecutive months are not independent", body: [
    "A wet month is often followed by another wet month, and a warm spell lingers. This is called autocorrelation. Standard tests assume independent observations, so positive autocorrelation makes a trend look more certain than it is.",
    "KALYX measures the lag-1 autocorrelation of the detrended residuals and, when it is positive, widens the Mann-Kendall variance accordingly (capped). It uses the residuals so that a genuine trend alone does not inflate the correction. This is a simplified adjustment. Specialist methods (such as Hamed-Rao or Yue-Wang) handle more lags and are worth using for formal research." ] },
  { title: "Many map cells, many tests: false discoveries", body: [
    "If you test 100 map cells at the 5% level, you expect about five to look significant even when nothing is happening. The more cells you test, the more false alarms.",
    "KALYX applies the Benjamini-Hochberg procedure, which controls the expected share of false discoveries among the cells it calls significant. Cells outlined in white on the trend map passed this stricter test. Cells that were only marginal are shown without an outline." ] },
  { title: "Point, area average, and pixel map", body: [
    "A point analysis uses one location. An area analysis averages all grid cells inside your drawn polygon. Cells nearer the poles cover less ground, so KALYX weights each cell by the cosine of its latitude.",
    "A pixel map tests every cell separately. This reveals patterns an average can hide: one part of a basin may be getting wetter while another gets drier, and the average can show no change at all. The area average and the pixel map answer different questions; use both." ] },
  { title: "The NASA datasets KALYX is built around", body: [
    "GPM IMERG combines satellite microwave and infrared observations into gridded precipitation, from 1998 to the present, at 0.1° resolution. Monthly values are rates in mm per hour, which KALYX converts to mm per month.",
    "MODIS (on NASA's Terra and Aqua satellites) measures land surface temperature at about 1 km. MOD11A2 is an 8-day composite, so KALYX aggregates it to monthly means after removing cloudy or low-quality pixels. Land surface temperature is the skin temperature of the ground, not the air temperature measured by weather stations.",
    "MERRA-2 is a reanalysis: a weather model constrained by observations, giving consistent land-surface variables such as soil wetness and runoff from 1980 at roughly 0.5° resolution. GLDAS is a land-surface model driven by observed meteorology, offering evapotranspiration, soil moisture and related fields. Both are model-based estimates, not direct measurements, and their coarse grids average over landscapes that may be much more varied." ] },
  { title: "Data quality and units", body: [
    "Satellite files include quality flags, fill values for missing data, and scale factors. For example, MODIS land surface temperature is stored as a scaled integer in kelvin, so the value is multiplied by 0.02 and converted to °C. Using raw numbers or keeping cloud-contaminated pixels can produce misleading trends.",
    "KALYX reports how many rows were valid and why others were dropped. Precipitation is summed over a month while temperature is averaged; mixing these up gives wrong results. Check every imported file's documentation before trusting the output." ] },
  { title: "Resolution and coverage differ between datasets", body: [
    "A 1 km product and a 50 km model grid do not show the same level of detail, even when drawn on the same map. Different datasets also start in different years, so comparisons must use the common period. KALYX shows each dataset's resolution and coverage in the Discover section." ] },
  { title: "What a significant trend does not tell you", body: [
    "A trend test shows that a variable changed in a consistent direction. It does not say why. Rising temperature alongside falling soil moisture is consistent with several explanations, including drought, land use, irrigation and changes in measurement. Causation needs additional evidence beyond a correlation or a trend.",
    "Likewise, a non-significant result is not proof of stability. Treat results as a starting point for questions, not as final conclusions." ] },
  { title: "A good investigation, step by step", body: [
    "1. Write a question (for example, “Is rainfall in this basin decreasing?”). 2. Choose a variable that actually measures it. 3. Select a place, or draw an area. 4. Choose at least 15 to 20 years of data where available. 5. Turn on seasonal handling. 6. Run the analysis and read both the slope and the p-value. 7. Check the data-quality summary. 8. Look at the pixel map for local differences. 9. Download the report and note the limitations." ] },
  { title: "Glossary", body: [
    "Anomaly: a value minus the long-term average for that time of year. Confidence interval: a range that, under the model's assumptions, would contain the true value 95% of the time across repeated studies. FDR: the expected fraction of false positives among results called significant. p-value: the probability of seeing a result at least this strong if there were no real trend. Reanalysis: a model-based reconstruction of past conditions that assimilates observations. Spatial resolution: the size of one grid cell. Temporal resolution: how often a value is recorded." ] },
  { title: "Frequently asked questions", body: [
    "Why is my result different from a published paper? Differences in dataset version, period, quality filtering, area, aggregation and test choice can all change results. Record these settings; the PDF report does.",
    "Why does the simulated demo show a trend? It is built with a known built-in trend to demonstrate the pipeline. It is labelled as simulated and is not NASA data.",
    "Why is the area average different from a nearby point? A point reflects one location's local variation; an area average smooths over many cells.",
    "How long should the record be? At least 10 years is required by KALYX, and 20 or more is much better for climate-scale trends." ] },
];
export default function Learn() {
  return (<section id="learn" className="wrap"><div className="split"><div><p className="eye">Method and background</p><h2>Learn</h2><p className="sub">How KALYX turns satellite records into evidence, what its tests mean, and where they can mislead.</p></div>
    <div>{SECTIONS.map((s, i) => <details className="acc" key={s.title} open={i === 0}><summary>{s.title}</summary>{s.body.map((t, j) => <p key={j}>{t}</p>)}</details>)}</div></div></section>);
}

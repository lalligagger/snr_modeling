import numpy as np
import pandas as pd
import pathlib
import plotly.express as px
from pyspectral.blackbody import blackbody
from pyspectral.solar import SolarIrradianceSpectrum, TOTAL_IRRADIANCE_SPECTRUM_2000ASTM
from scipy import interpolate
from spectral import EcostressDatabase


# wl_min = 0.41
# wl_max = 14.0

wl_min = 9.5
wl_max = 14.0

d_lambda = 0.005

wavelengths = np.arange(wl_min, wl_max, d_lambda)
bb_temp = 300

# get relative data folder
PATH = pathlib.Path(__file__).parent
DATA_PATH = PATH.joinpath("./datasets").resolve()

atm_trans = pd.read_csv('./datasets/modtran_lwir.csv')

db = EcostressDatabase(DATA_PATH.joinpath("ecostress.db"))
s = db.get_signature(134)
spectrum_plot = px.line(x=s.x, y=s.y).update_layout(
    title_text=s.sample_name,
    xaxis_title="Wavelength [microns]",
    yaxis_title="Reflectance [%]",
)

bb_rads = blackbody(wavelengths * 1e-6, bb_temp) * 1e-6
solar_irr = SolarIrradianceSpectrum(
    TOTAL_IRRADIANCE_SPECTRUM_2000ASTM, dlambda=0.0005
)  # , wavespace='wavenumber')
scene_refl = db.get_signature(579)

refl_line = px.line(x=s.x, y=s.y).update_layout(
    title_text=s.sample_name,
    xaxis_title="Wavelength [microns]",
    yaxis_title="Reflectance [%]",
)

bb_line = px.line(x=wavelengths, y=bb_rads)
solar_line = px.line(
    x=solar_irr.wavelength, y=solar_irr.irradiance, range_x=[0, 14]
)  # , log_y=True)

# DEBUG Plots
# refl_line.show()
# solar_line.show()
# bb_line.show()

spectral_function = interpolate.interp1d(solar_irr.wavelength, solar_irr.irradiance)
refl_function = interpolate.interp1d(s.x, s.y)
atm_function = interpolate.interp1d(atm_trans.x, atm_trans.y)
refl_resamp = refl_function(wavelengths)
solar_resamp = spectral_function(wavelengths)
atm_resamp = atm_function(wavelengths)

df = (
    pd.DataFrame(
        data=[solar_resamp, refl_resamp, bb_rads, atm_resamp*100, wavelengths],
        index=["solar_rad", "scene_refl", "bb_rad", "atm_trans", "wave_um"],
    )
    .transpose()
    .set_index("wave_um")
)  # , index=[wavelengths])

df["solar_reflected"] = df["solar_rad"] * (df["scene_refl"] / 100) * (df["atm_trans"] / 100)
df["emissivity"] = df["scene_refl"] * (-1) + 100
df["emitted_thermal"] = df["bb_rad"] * (df["emissivity"] / 100)
df["at_lens"] = (df["emitted_thermal"] + df["solar_reflected"])*df["atm_trans"]/100

print(df.head())

fig = px.line(df, log_y=True, range_y=[1e-6,1e5]).update_layout(
    title_text="Scene Spectrum: {} , Scene Temperature: {}".format(
        s.sample_name, bb_temp
    ),
    xaxis_title="Wavelength [microns]",
    yaxis_title="Radiance [W/m^2/um/sr] ; Reflectance/ Emissivity [%]",
)
fig.show()

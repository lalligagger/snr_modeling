import numpy as np
from pint import UnitRegistry
from scipy import integrate

# import plotly.express as px
import pandas as pd

# Create unit registry. Can be accessed using HYTRAN.ureg on import, must use same ureg for calcs.
ureg = UnitRegistry()

# Define often-used constants

h = ureg.planck_constant
# planck_constant = 6.62607015e-34 J s = h                      # since May 2019

c_0 = ureg.c
# speed_of_light = 299792458 m/s = c = c_0                      # since 1983

k_B = ureg.boltzmann_constant
# boltzmann_constant = 1.380649e-23 J K^-1 = k = k_B            # since May 2019

# F = 1


class Instrument:
    """Instrument class for SNR analysis. Follows Schott G-factors for lens/ Cassegrain telescope."""

    def __init__(self, f_no=1, bb_trans=0.8, fl_mm=180, kind="lens"):
        # First-order optical properties
        self.f_no = f_no
        self.focal_length_mm = fl_mm
        self.transmission = bb_trans
        # Can be used to switch between first-order G_factor
        self.kind = kind

        if self.kind == "lens":
            self.G_factor = 4 * self.f_no ** 2 / self.transmission  # / ureg.steradian

        elif self.kind == "cassegrain":
            # Assumes 70% transmission after obscuration for now
            self.G_factor = (1 + 4 * self.f_no ** 2) / (
                0.7 * self.transmission
            )  # / ureg.steradian

    def add_detector(self, name="ubol", pp_um=17, t_int_us=12, detectivity=8e8):
        """Adds detector to instrument model (in work)."""
        self.pp_um = pp_um * ureg.micrometer
        self.A_det = (self.pp_um) ** 2
        self.t_int_us = t_int_us * 1e-3 * ureg.second
        # TODO: Add Jones to ureg.
        self.detectivity = detectivity * (ureg.Hz ** 0.5 * ureg.centimeter / ureg.watt)
        self.bandwidth_hz = 1 / (self.t_int_us)

    def calc_NEP(self):
        NEP = (self.A_det * self.bandwidth_hz) ** 0.5 / self.detectivity
        NEP = NEP.to(ureg.watt)
        self.NEP = NEP
        return NEP

    def add_band(self, wavs, transmission, name="test_band"):
        print("just a test")

    def integrate_flux(self, spectral_radiance):
        """Integrates flux on detector, given in [Watt/micrometer]"""
        # G-factor is a constant for now. Eventually will need to re-sample everything on same WL scale.
        spectral_flux = spectral_radiance * self.A_detector / self.G_factor
        return spectral_flux


class Scene:
    def gen_spectral_radiant_density(self, wav, T):
        # def plancks_law(wav, T):
        """
        Planks Law for a blackbody. Outputs the spectral radiant density of a blackbody surface
        at given temp and wavelength.
        From equation 4.2.1 of SE Approach to Imaging, or Schott 3.3.4 "Magic pi"

        Parameters:
        wav (float): wavelength [micrometer]
        T (float): temperature [Kelvin]

        Returs:
        density: spectral radiant density [Joule / meter^3 / Hz]
        """
        # Input units need to be attached to the same ureg as constants. Could we hand off tuple?
        T = T * ureg.kelvin
        wav = wav * ureg.micrometer
        a = 8 * np.pi * ureg.h * ureg.c_0
        b = ureg.h * ureg.c_0 / (wav * ureg.k_B * T)
        density = a / ((wav ** 5) * (np.exp(b) - 1.0))
        density = density.to(ureg.joule / ureg.meter ** 3 / ureg.micrometer)
        return density

    def gen_spectral_power(self, wav, T, view=2 * np.pi * ureg.steradian):
        """
        Computes the spectral radiant exitance into a unit solid angle for Lambertian blackbody.
        From Schott Eqn. 3.24. Integrate over waveband for power. Per Schott 3.2.2 this must be done numerically.

        Parameters:
        wav (float): wavelength [micrometer]
        T (float): temperature [Kelvin]
        view (float): view factor solid angle [steradian]

        Returns:
        spectral_power: power into solid angle [W / meter^2 / micrometer]

        """
        T = T * ureg.kelvin
        wav = wav * ureg.micrometer
        unit_solid_angle = 1 * ureg.steradian
        a = 2.0 * h * c_0 ** 2
        b = h * c_0 / (wav * k_B * T)
        spectral_power = a / ((wav ** 5) * (np.exp(b) - 1.0))
        spectral_power = spectral_power.to(
            ureg.watt / (ureg.meter ** 2 * ureg.micrometer)
        )

        self.ext_power_bb = [wav, spectral_power]
        # spectral_power = spectral_power * (view / unit_solid_angle)
        return spectral_power, wav

    def integrate_spectral_intensity(self, spectral_power, wavs, band_um):
        """
        Integrate a spectral power curve over some waveband. Requires two arrays of spectral power and wavelengths.

        Parameters:
        spectral_power (array): spectral intensity to integrate [W / meter^2 / micrometer]
        wavs (array): domain for the spectral intensity data [micrometer]

        Returns:
        radiant exitance (float): integrated power per area in the band [W/ meter^2]
        """

        # TODO: Filter by band.
        # spectral_power = spectral_power.to_tuple()[0]
        # wavs = wavs.to_tuple()[0]
        # df = pd.DataFrame(data=spectral_power, index=wavs)

        # if band_um == None:
        #     # Integrate the full wavs domain
        #     band_um = [wavs[0], wavs[-1]]

        # df = df.loc[(df.index < band_um[0]) & (df.index > band_um[1])]

        exitance = integrate.trapezoid(
            wavs, spectral_power
        )  # does this track units?! - it does!!!
        # exitance = integrate.trapezoid(df.index.values, df[0])
        # return df
        exitance = exitance.to(ureg.watts / ureg.meter ** 2)
        return exitance

    def apply_spectra(self, spectra_dict={'aster_id':579, 'pixel_fill': 1.0}):
        # for s in spectra:
        s = db.get_signature(spectra_dict['aster_id'])

        # resample to same wl scale
        # generate new x,y on scenario sampling. needs to handle over/ undersampling
        s_resamp = resample(s.x, s.y, new_dx) 
        # apply the resampled spectra to scene power/ irradiance (shouldhanlde any of these!)
        self.ext_power_pix = self.ext_power_bb * s_resamp


class Scenario:
    def rx_detector_power_greybody(
        self, Instrument, T_scene, wl1, wl2, emmissivity=1.0
    ):
        # Schott 5.50 states that the spectral flux on a detector is given by...

        # for band in Instrument.bands:

        # Figure of merit for optics. Will come from separate instrument model.
        # G_optics = 31 / unit_solid_angle
        G_optics = Instrument.G_factor
        # A_det = (17 * micron) ** 2
        A_det = Instrument.A_det

        d_lambda = (wl2 - wl1) * ureg.micrometer
        L1, wl1 = Scene.gen_spectral_power(self, wl1, T_scene)
        L2, wl1 = Scene.gen_spectral_power(self, wl2, T_scene)

        integrated_spectral_radiance = (
            ((L1 + L2) / 2) * emmissivity * d_lambda
        )  # TODO: Change to integrate.trapezoid
        omega = integrated_spectral_radiance * A_det / G_optics

        # omega = omega.to(ureg.watt)

        return omega

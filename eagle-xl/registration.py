"""
Registration of extra quantities for velociraptor catalogues (i.e. quantities
derived from the catalogue's internal properties).
This file calculates:
    + sSFR (30, 100 kpc) (specific_sfr_gas_{x}_kpc)
        This is the specific star formation rate of gas within those apertures.
        Only calculated for galaxies with a stellar mass greater than zero.
    + is_passive and is_active (30, 100 kpc) (is_passive_{x}_kpc)
        Boolean that determines whether or not a galaxy is passive. Marginal
        specific star formation rate is 1e-11 year^-1.
    + sfr_halo_mass (30, 100 kpc) (sfr_halo_mass_{x}_kpc)
        Star formation rate divided by halo mass with the star formation rate
        computed within apertures.
    + 12 + log(O/H) ({gas_sf_twelve_plus_log_OH_{x}_kpc, 30, 100 kpc)
        12 + log(O/H) based on metallicities. These should be removed at some point
        once velociraptor has a more sensible way of dealing with metallicity
        units.
    + metallicity_in_solar (star_metallicity_in_solar_{x}_kpc, 30, 100 kpc)
        Metallicity in solar units (relative to metal_mass_fraction).
    + stellar_mass_to_halo_mass_{x}_kpc for 30 and 100 kpc
        Stellar Mass / Halo Mass (mass_200crit and mass_BN98) for 30 and 100 kpc apertures.
    + HI and H_2 masses (gas_HI_mass_Msun and gas_H2_mass_Msun).
    + baryon and gas fractions in R_(200,cr) normalized by the
        cosmic baryon fraction (baryon_fraction_true_R200, gas_fraction_true_R200).
"""

# Aperture sizes in kpc in which stellar mass is computed
aperture_sizes = [30, 100]

# Specific star formation rate in apertures, as well as passive fraction
marginal_ssfr = unyt.unyt_quantity(1e-11, units=1 / unyt.year)

for aperture_size in aperture_sizes:
    halo_mass = catalogue.masses.mass_200crit

    stellar_mass = getattr(catalogue.apertures, f"mass_star_{aperture_size}_kpc")
    # Need to mask out zeros, otherwise we get RuntimeWarnings
    good_stellar_mass = stellar_mass > unyt.unyt_quantity(0.0, stellar_mass.units)

    star_formation_rate = getattr(catalogue.apertures, f"sfr_gas_{aperture_size}_kpc")

    ssfr = np.ones(len(star_formation_rate)) * marginal_ssfr
    ssfr[good_stellar_mass] = (
        star_formation_rate[good_stellar_mass] / stellar_mass[good_stellar_mass]
    )
    ssfr[ssfr < marginal_ssfr] = marginal_ssfr
    ssfr.name = f"Specific SFR ({aperture_size} kpc)"

    is_passive = unyt.unyt_array(
        (ssfr < 1.01 * marginal_ssfr).astype(float), units="dimensionless"
    )
    is_passive.name = "Passive Fraction"

    is_active = unyt.unyt_array(
        (ssfr > 1.01 * marginal_ssfr).astype(float), units="dimensionless"
    )
    is_active.name = "Active Fraction"

    sfr_M200 = star_formation_rate / halo_mass
    sfr_M200.name = "Star formation rate divided by halo mass"

    setattr(self, f"specific_sfr_gas_{aperture_size}_kpc", ssfr)
    setattr(self, f"is_passive_{aperture_size}_kpc", is_passive)
    setattr(self, f"is_active_{aperture_size}_kpc", is_active)
    setattr(self, f"sfr_halo_mass_{aperture_size}_kpc", sfr_M200)

# Now metallicities relative to different units

solar_metal_mass_fraction = 0.0126
twelve_plus_log_OH_solar = 8.69
minimal_twelve_plus_log_OH = 7.5

for aperture_size in aperture_sizes:
    try:
        metal_mass_fraction_star = (
            getattr(catalogue.apertures, f"zmet_star_{aperture_size}_kpc")
            / solar_metal_mass_fraction
        )
        metal_mass_fraction_star.name = f"Star Metallicity $Z_*$ rel. to $Z_\\odot={solar_metal_mass_fraction}$ ({aperture_size} kpc)"
        setattr(
            self,
            f"star_metallicity_in_solar_{aperture_size}_kpc",
            metal_mass_fraction_star,
        )
    except AttributeError:
        pass

    try:
        metal_mass_fraction_gas = (
            getattr(catalogue.apertures, f"zmet_gas_sf_{aperture_size}_kpc")
            / solar_metal_mass_fraction
        )

        # Handle scenario where metallicity is zero, as we are bounded
        # by approx 1e-2 metal mass fraction anyway:
        metal_mass_fraction_gas[metal_mass_fraction_gas < 1e-5] = 1e-5

        log_metal_mass_fraction_gas = np.log10(metal_mass_fraction_gas.value)
        twelve_plus_log_OH = unyt.unyt_array(
            twelve_plus_log_OH_solar + log_metal_mass_fraction_gas,
            units="dimensionless",
        )
        twelve_plus_log_OH.name = f"Gas (SF) $12+\\log_{{10}}$O/H from $Z$ (Solar={twelve_plus_log_OH_solar}) ({aperture_size} kpc)"

        twelve_plus_log_OH[
            twelve_plus_log_OH < minimal_twelve_plus_log_OH
        ] = minimal_twelve_plus_log_OH

        setattr(
            self, f"gas_sf_twelve_plus_log_OH_{aperture_size}_kpc", twelve_plus_log_OH
        )
    except AttributeError:
        pass


# Now stellar mass - halo mass relation

for aperture_size in aperture_sizes:
    stellar_mass = getattr(catalogue.apertures, f"mass_star_{aperture_size}_kpc")
    halo_mass = catalogue.masses.mass_200crit

    halo_M200crit = catalogue.masses.mass_200crit
    smhm = stellar_mass / halo_mass
    name = f"$M_* / M_{{\\rm 200crit}}$ ({aperture_size} kpc)"
    smhm.name = name
    setattr(self, f"stellar_mass_to_halo_mass_200crit_{aperture_size}_kpc", smhm)

    halo_MBN98 = catalogue.masses.mass_bn98
    smhm = stellar_mass / halo_MBN98
    name = f"$M_* / M_{{\\rm BN98}}$ ({aperture_size} kpc)"
    smhm.name = name
    setattr(self, f"stellar_mass_to_halo_mass_bn98_{aperture_size}_kpc", smhm)

# Now HI masses

gas_mass = catalogue.masses.m_gas
nonmetal_frac = 1.0 - catalogue.apertures.zmet_gas_sf_100_kpc
try:
    H_frac = getattr(catalogue.element_mass_fractions, "element_0")
    hydrogen_frac_error = ""
except:
    H_frac = 0.0
    hydrogen_frac_error = "(no H abundance)"

try:
    # Test for CHIMES arrays
    HI_species_frac = catalogue.species_fractions.species_1
    species_frac_error = ""
except:
    try:
        # Test for COLIBRE arrays
        HI_species_frac = catalogue.species_fractions.species_0
        species_frac_error = ""
    except:
        HI_species_frac = catalogue.species_fractions.species_1
        species_frac_error = "(no species field)"

total_error = f" {species_frac_error}{hydrogen_frac_error}"
HI_mass = gas_mass * H_frac * HI_species_frac
HI_mass.name = f"$M_{{\\rm HI}}${total_error}"

HI_mass_wHe = gas_mass * nonmetal_frac * HI_species_frac
HI_mass_wHe.name = f"$M_{{\\rm HI}}${total_error}"

setattr(self, "gas_HI_mass", HI_mass)
setattr(self, "gas_HI_plus_He_mass", HI_mass_wHe)

# Now H2 masses

gas_mass = catalogue.masses.m_gas
nonmetal_frac = 1.0 - catalogue.apertures.zmet_gas_sf_100_kpc
try:
    H_frac = getattr(catalogue.element_mass_fractions, "element_0")
    hydrogen_frac_error = ""
except:
    H_frac = 0.0
    hydrogen_frac_error = "(no H abundance)"

try:
    # Test for CHIMES arrays
    H2_species_frac = catalogue.species_fractions.species_7
    species_frac_error = ""
except:
    try:
        # Test for COLIBRE arrays
        H2_species_frac = catalogue.species_fractions.species_0
        species_frac_error = ""
    except:
        H2_species_frac = catalogue.species_fractions.species_2
        species_frac_error = "(no species field)"

total_error = f" {species_frac_error}{hydrogen_frac_error}"
H2_mass = (
    gas_mass * H_frac * H2_species_frac * 2
)  # Factor of 2 to convert H2 species fraction to mass fraction
H2_mass_wHe = (
    gas_mass * nonmetal_frac * H2_species_frac * 2
)  # Factor of 2 to convert H2 species fraction to mass fraction

H2_mass.name = f"$M_{{\\rm H_2}}{total_error}$"
H2_mass_wHe.name = f"$M_{{\\rm H_2}}{total_error}$"

setattr(self, "gas_H2_mass", H2_mass)
setattr(self, "gas_H2_plus_He_mass", H2_mass_wHe)

# Now neutral H masses and fractions

try:
    gas_mass = catalogue.masses.m_gas
    H_frac = getattr(catalogue.element_mass_fractions, "element_0")

    # Try CHIMES arrays
    if hasattr(catalogue.species_fractions, "species_7"):
        HI_species_frac = getattr(catalogue.species_fractions, "species_1")
        H2_species_frac = getattr(catalogue.species_fractions, "species_7")
    # If species_7 doesn't exist, switch to the (default) Table-cooling case
    else:
        HI_species_frac = getattr(catalogue.species_fractions, "species_0")
        H2_species_frac = getattr(catalogue.species_fractions, "species_2")

    HI_mass = gas_mass * H_frac * HI_species_frac
    H2_mass = gas_mass * H_frac * H2_species_frac * 2
    neutral_H_mass = HI_mass + H2_mass
    neutral_H_mass.name = "$M_{\\rm HI + H_2}$"

    setattr(self, "gas_neutral_H_mass", neutral_H_mass)

    for aperture_size in aperture_sizes:
        stellar_mass = getattr(catalogue.apertures, f"mass_star_{aperture_size}_kpc")
        neutral_H_to_stellar_fraction = neutral_H_mass / stellar_mass
        neutral_H_to_stellar_fraction.name = (
            f"$M_{{\\rm HI + H_2}} / M_*$ ({aperture_size} kpc)"
        )

        molecular_H_to_molecular_plus_stellar_fraction = H2_mass / (
            H2_mass + stellar_mass
        )
        molecular_H_to_molecular_plus_stellar_fraction.name = (
            f"$M_{{\\rm H_2}} / (M_* + M_{{\\rm H_2}})$ ({aperture_size} kpc)"
        )

        molecular_H_to_neutral_fraction = H2_mass / neutral_H_mass
        molecular_H_to_neutral_fraction.name = (
            f"$M_{{\\rm H_2}} / M_{{\\rm HI + H_2}}$ ({aperture_size} kpc)"
        )

        setattr(
            self,
            f"gas_neutral_H_to_stellar_fraction_{aperture_size}_kpc",
            neutral_H_to_stellar_fraction,
        )
        setattr(
            self,
            f"gas_molecular_H_to_molecular_plus_stellar_fraction_{aperture_size}_kpc",
            molecular_H_to_molecular_plus_stellar_fraction,
        )
        setattr(
            self,
            f"gas_molecular_H_to_neutral_fraction_{aperture_size}_kpc",
            molecular_H_to_neutral_fraction,
        )

except AttributeError:
    # We did not produce these quantities.
    setattr(
        self,
        "gas_neutral_H_mass",
        unyt.unyt_array(
            catalogue.masses.m_gas,
            name="$M_{\\rm HI + H_2}$ not found, showing $M_{\\rm g}$",
        ),
    )
    # We did not produce these fractions, let's make an arrays of ones.
    ones = unyt.unyt_array(
        np.ones(np.size(catalogue.masses.mass_200crit)), "dimensionless"
    )
    for aperture_size in aperture_sizes:
        setattr(
            self,
            f"gas_neutral_H_to_stellar_fraction_{aperture_size}_kpc",
            unyt.unyt_array(
                np.ones_like(catalogue.masses.m_gas),
                name="$M_{{\\rm HI + H_2}} / M_*$ ({aperture_size} kpc) not found, showing $1$",
                units="dimensionless",
            ),
        )
        setattr(
            self,
            f"gas_molecular_H_to_molecular_plus_stellar_fraction_{aperture_size}_kpc",
            unyt.unyt_array(
                np.ones_like(catalogue.masses.m_gas),
                name=f"$M_{{\\rm H_2}} / (M_* + M_{{\\rm H_2}})$ ({aperture_size} kpc) not found, showing $1$",
                units="dimensionless",
            ),
        )
        setattr(
            self,
            f"gas_molecular_H_to_neutral_fraction_{aperture_size}_kpc",
            unyt.unyt_array(
                np.ones_like(catalogue.masses.m_gas),
                name=f"$M_{{\\rm H_2}} / M_{{\\rm HI + H_2}}$ ({aperture_size} kpc) not found, showing $1$",
                units="dimensionless",
            ),
        )

# species fraction properties
gas_mass = catalogue.apertures.mass_gas_100_kpc
gal_area = (
    2 * np.pi * catalogue.projected_apertures.projected_1_rhalfmass_star_100_kpc ** 2
)
mstar_100 = catalogue.projected_apertures.projected_1_mass_star_100_kpc

# Selection functions for the xGASS and xCOLDGASS surveys, used for the H species fraction comparison.
# Note these are identical mass selections, but are separated to keep survey selections explicit
# and to allow more detailed selection criteria to be added for each.

self.xgass_galaxy_selection = np.logical_and(
    catalogue.apertures.mass_star_100_kpc > unyt.unyt_quantity(10 ** 9, "Solar_Mass"),
    catalogue.apertures.mass_star_100_kpc
    < unyt.unyt_quantity(10 ** (11.5), "Solar_Mass"),
)

self.xcoldgass_galaxy_selection = np.logical_and(
    catalogue.apertures.mass_star_100_kpc > unyt.unyt_quantity(10 ** 9, "Solar_Mass"),
    catalogue.apertures.mass_star_100_kpc
    < unyt.unyt_quantity(10 ** (11.5), "Solar_Mass"),
)

self.mu_star_100_kpc = mstar_100 / gal_area
self.mu_star_100_kpc.name = "$\\pi R_{*, 100 {\\rm kpc}}^2 / M_{*, 100 {\\rm kpc}}$"

try:
    H_frac = catalogue.element_mass_fractions.element_0
    hydrogen_frac_error = ""
except:
    H_frac = 0.0
    hydrogen_frac_error = "(no H abundance)"

try:
    # Test for CHIMES arrays
    species_HI = catalogue.species_fractions.species_1
    species_H2 = 2.0 * catalogue.species_fractions.species_7
    species_frac_error = ""
except:
    try:
        # Test for COLIBRE arrays
        species_HI = catalogue.species_fractions.species_0
        species_H2 = 2.0 * catalogue.species_fractions.species_2
        species_frac_error = ""
    except:
        species_HI = 0.0
        species_H2 = 0.0
        species_frac_error = "(no species field)"

total_error = f" {species_frac_error}{hydrogen_frac_error}"

self.neutral_hydrogen_mass_100_kpc = gas_mass * H_frac * species_HI
self.hi_to_stellar_mass_100_kpc = (
    self.neutral_hydrogen_mass_100_kpc / catalogue.apertures.mass_star_100_kpc
)
self.molecular_hydrogen_mass_100_kpc = gas_mass * H_frac * species_H2
self.h2_to_stellar_mass_100_kpc = (
    self.molecular_hydrogen_mass_100_kpc / catalogue.apertures.mass_star_100_kpc
)

self.neutral_hydrogen_mass_100_kpc.name = f"HI Mass (100 kpc){total_error}"
self.hi_to_stellar_mass_100_kpc.name = f"$M_{{\\rm HI}} / M_*$ (100 kpc) {total_error}"
self.molecular_hydrogen_mass_100_kpc.name = f"H$_2$ Mass (100 kpc){total_error}"
self.h2_to_stellar_mass_100_kpc.name = f"$M_{{\\rm H_2}} / M_*$ (100 kpc) {total_error}"

# Now baryon fractions

try:
    Omega_m = catalogue.units.cosmology.Om0
    Omega_b = catalogue.units.cosmology.Ob0

    M_500 = catalogue.spherical_overdensities.mass_500_rhocrit
    M_500_gas = catalogue.spherical_overdensities.mass_gas_500_rhocrit
    M_500_star = catalogue.spherical_overdensities.mass_star_500_rhocrit
    M_500_baryon = M_500_gas + M_500_star

    f_b_500 = (M_500_baryon / M_500) / (Omega_b / Omega_m)
    name = "$f_{\\rm b, 500, true} / (\\Omega_{\\rm b} / \\Omega_{\\rm m})$"
    f_b_500.name = name

    f_gas_500 = (M_500_gas / M_500) / (Omega_b / Omega_m)
    name = "$f_{\\rm gas, 500, true} / (\\Omega_{\\rm b} / \\Omega_{\\rm m})$"
    f_gas_500.name = name

    setattr(self, "baryon_fraction_true_R500", f_b_500)
    setattr(self, "gas_fraction_true_R500", f_gas_500)
except AttributeError:
    # We did not produce these quantities, let's make an array of ones.
    ones = unyt.unyt_array(
        np.ones(np.size(catalogue.masses.mass_200crit)), "dimensionless"
    )
    setattr(
        self,
        "baryon_fraction_true_R500",
        unyt.unyt_array(
            ones,
            name="$f_{\\rm b, 500, true} / (\\Omega_{\\rm b} / \\Omega_{\\rm m})$ not found, showing $1$",
        ),
    )
    setattr(
        self,
        "gas_fraction_true_R500",
        unyt.unyt_array(
            ones,
            name="$f_{\\rm gas, 500, true} / (\\Omega_{\\rm b} / \\Omega_{\\rm m})$ not found, showing $1$",
        ),
    )

"""
Plots the stellar abundances ([O/H] vs [Mg/Fe]) for a given snapshot
"""
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import numpy as np
import unyt
import glob
from swiftsimio import load
from swiftpipeline.argumentparser import ScriptArgumentParser
from velociraptor.observations import load_observations


def read_data(data):
    """
    Grabs the data
    """

    mH_in_cgs = unyt.mh
    mFe_in_cgs = 55.845 * unyt.mp
    mO_in_cgs = 15.999 * unyt.mp
    mMg_in_cgs = 24.305 * unyt.mp

    # Asplund et al. (2009)
    Fe_H_Sun_Asplund = 7.5
    Mg_H_Sun_Asplund = 7.6
    O_H_Sun_Asplund = 8.69

    Mg_Fe_Sun = Mg_H_Sun_Asplund - Fe_H_Sun_Asplund - np.log10(mFe_in_cgs / mMg_in_cgs)
    O_H_Sun = O_H_Sun_Asplund - 12.0 - np.log10(mH_in_cgs / mO_in_cgs)

    magnesium = data.stars.element_mass_fractions.magnesium
    iron = data.stars.element_mass_fractions.iron
    oxygen = data.stars.element_mass_fractions.oxygen
    hydrogen = data.stars.element_mass_fractions.hydrogen

    O_H = np.log10(oxygen / hydrogen) - O_H_Sun
    Mg_Fe = np.log10(magnesium / iron) - Mg_Fe_Sun

    O_H[oxygen == 0] = -7  # set lower limit
    O_H[O_H < -7] = -7  # set lower limit

    Mg_Fe[iron == 0] = -2  # set lower limit
    Mg_Fe[magnesium == 0] = -2  # set lower limit
    Mg_Fe[Mg_Fe < -2] = -2  # set lower limit

    return O_H, Mg_Fe


arguments = ScriptArgumentParser(
    description="Creates an [Fe/H] - [Mg/Fe] plot for stars."
)

snapshot_filenames = [
    f"{directory}/{snapshot}"
    for directory, snapshot in zip(arguments.directory_list, arguments.snapshot_list)
]

names = arguments.name_list
output_path = arguments.output_directory

plt.style.use(arguments.stylesheet_location)

simulation_lines = []
simulation_labels = []

fig, ax = plt.subplots()
ax.grid(True)

for snapshot_filename, name in zip(snapshot_filenames, names):

    data = load(snapshot_filename)
    redshift = data.metadata.z

    O_H, Mg_Fe = read_data(data)

    # low zorder, as we want these points to be in the background
    dots = ax.plot(O_H, Mg_Fe, ".", markersize=0.2, alpha=0.2, zorder=-99)[0]

    # Bins along the X axis (O_H) to plot the median line
    bins = np.arange(-7.2, 1, 0.2)
    ind = np.digitize(O_H, bins)

    xm, ym = [], []
    Min_N_points_per_bin = 11

    for i in range(1, len(bins)):
        in_bin_idx = ind == i
        N_data_points_per_bin = np.sum(in_bin_idx)
        if N_data_points_per_bin >= Min_N_points_per_bin:
            xm.append(np.median(O_H[in_bin_idx]))
            ym.append(np.median(Mg_Fe[in_bin_idx]))

    # high zorder, as we want the simulation lines to be on top of everything else
    # we steal the color of the dots to make sure the line has the same color
    simulation_lines.append(
        ax.plot(
            xm,
            ym,
            lw=2,
            color=dots.get_color(),
            zorder=1000,
            path_effects=[pe.Stroke(linewidth=4, foreground="white"), pe.Normal()],
        )[0]
    )
    simulation_labels.append(f"{name} ($z={redshift:.1f}$)")

ax.set_xlabel("[O/H]")
ax.set_ylabel("[Mg/Fe]")

ax.set_ylim(-2.0, 3.0)
ax.set_xlim(-7.2, 2.0)

observation_legend = ax.legend(markerfirst=True, loc="upper left")

ax.add_artist(observation_legend)

simulation_legend = ax.legend(
    simulation_lines, simulation_labels, markerfirst=False, loc="lower left"
)

ax.add_artist(simulation_legend)

plt.savefig(f"{output_path}/stellar_abundances_OH_MgFe.png")

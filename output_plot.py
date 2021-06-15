import pandas as pd
import matplotlib.pyplot as plt
import sys
filename = sys.argv[-1]
# filename = "dist/output/output_2021-01-21_18点25分45秒.csv"
output = pd.read_csv(filename)
output.index = output.time
output.voltage.plot()
output.current.plot()
output.power.plot()
plt.show()
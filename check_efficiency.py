#!/usr/bin/env python3
import subprocess
import datetime
import pandas as pd
from io import StringIO
from sys import argv
from tabulate import tabulate

user = argv[1]
start  = datetime.date.today() - datetime.timedelta(days = int(argv[2]))
 
date_str = start.strftime("%Y-%m-%d")

fields = ['JobID',
'CPUTimeRAW',
'TotalCPU',
'JobName',
'NCPUS',
'ReqMem',
'ExitCode',
'TimeLimit']

formatstr = ','.join( f+"%20" for f in fields)

cmd = f"sacct -u {user} --start {date_str} -o {formatstr} --parsable"
output  = subprocess.run(cmd.split(), capture_output = True)
str_output = output.stdout.decode("utf-8")
ss = StringIO(str_output)

df = pd.read_csv(ss,delimiter="|")
#drop the last column
df = df.iloc[:,:-1]


index = df.JobID.str.extract("(?P<JobID>\d+)\.?(?P<Substep>.*)", expand = True)

df = df[[col for col in df.columns if col != "JobID"]].join(index).set_index(["JobID","Substep"])

print(df)

# Got the dataframe

# convert TimeRAW to timedelta

df.CPUTimeRAW = pd.to_timedelta(df.CPUTimeRAW,unit = 'sec')

# convert TotalCPU to timedelta
# complicated because the timedelta format of slurm and of pandas do not
# agree
units = ['days','hours','minutes','seconds']

days_pattern = r"(?P<days>\d*)-"
hours_pattern = r"(?P<hours>\d+):"
days_hour_pattern = f"({days_pattern})?{hours_pattern}"

minutes_pattern = r"(?P<minutes>\d+)"
seconds_pattern = r"(?P<seconds>.*)"

totcpu = df.TotalCPU.str.extract(
        f"({days_hour_pattern})?{minutes_pattern}:{seconds_pattern}",
        expand = True)[units]

totcpu[totcpu.isna()] = 0

df.TotalCPU = sum((pd.to_timedelta(totcpu[unit].astype(float), unit = unit) for unit in units),pd.Timedelta(0))

# Compute efficiency

df['Efficiency'] = df.TotalCPU/df.CPUTimeRAW

df["Effective CPUS"] = (df.Efficiency * df.NCPUS)

print(df.loc[(slice(None),''),['Efficiency','NCPUS','Effective CPUS','ReqMem','ExitCode','TimeLimit']])

print("Efficiency:", df.TotalCPU.loc[(slice(None),'')].sum()/df.CPUTimeRAW.loc[(slice(None),'')].sum())

out_df = df.loc[:,['Efficiency','NCPUS','Effective CPUS','ReqMem','ExitCode']]


with open(f"eff_{user}.csv",'w') as f:
    f.write(
            tabulate(out_df
                    .reset_index()
                    .sort_values(by=["JobID","Substep"]),
                    headers='keys',
                    tablefmt='psql',
                    showindex=False)
            )



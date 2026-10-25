"""Stable target identity; ON/OFF alone never identifies a four-cell choice."""
def label(environment,enabled):
 assert environment in ('N','E') and type(enabled) is bool
 return ('T1' if enabled else 'T0') if environment=='N' else ('T0' if enabled else 'T1')
def validate(row):
 assert row['target_label']==label(row['environment'],row['target_intervention_enabled']),'reversed target mapping'
 return True

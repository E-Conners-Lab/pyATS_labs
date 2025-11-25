from genie.harness.main import gRun

def main():
    gRun(
        trigger_uids=["TriggerShutNoShutOspf"],
        trigger_datafile="datafiles/ospf_trigger_datafile.yaml",
        verification_uids=["Verify_IpOspfDatabaseRouter"],
        verification_datafile="datafiles/ospf_verification_datafile.yaml",
    )
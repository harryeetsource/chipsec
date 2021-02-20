"""
SMM_Code_Chk_En is a bit found in the MSR_SMM_FEATURE_CONTROL register.
Once set to '1', any CPU that attempts to execute SMM code not within the ranges defined by the SMRR will assert an unrecoverable MCE.
As such, enabling and locking this bit is an important step in mitigating SMM call-out vulnerabilities.
This CHIPSEC module simply reads the register and checks that SMM_Code_Chk_En is set and locked.
"""
from chipsec.helper.oshelper import HWAccessViolationError
from chipsec.module_common import BaseModule, ModuleResult, MTAG_BIOS, MTAG_SMM

TAGS = [MTAG_BIOS, MTAG_SMM]

class smm_code_chk(BaseModule):

    def __init__(self):
        BaseModule.__init__(self)

    def is_supported(self):
        # The Intel SDM states that MSR_SMM_FEATURE_CONTROL can only be accessed while the CPU executes in SMM.
        # However, in reality many users report that there is no problem reading this register from outside of SMM.
        # Just to be on the safe side of things, we'll verify we can read this register successfully before moving on.
        try:
            self.cs.read_register( 'MSR_SMM_FEATURE_CONTROL' )
        except HWAccessViolationError:
            self.res = ModuleResult.NOTAPPLICABLE
            return False
        else:
            return True

    def _check_SMM_Code_Chk_En(self, thread_id):
        regval      = self.cs.read_register( 'MSR_SMM_FEATURE_CONTROL', thread_id )
        lock        = self.cs.get_register_field( 'MSR_SMM_FEATURE_CONTROL', regval, 'LOCK' )
        code_chk_en = self.cs.get_register_field( 'MSR_SMM_FEATURE_CONTROL', regval, 'SMM_Code_Chk_En' )

        self.cs.print_register( 'MSR_SMM_FEATURE_CONTROL', regval )

        if 1 == code_chk_en:
            if 1 == lock:
                res = ModuleResult.PASSED
            else:
                res = ModuleResult.FAILED
        else:
            # MSR_SMM_MCA_CAP (the register that reports enhanced SMM capabilities) can only be read from SMM.
            # Thus, there is no way to tell whether the the CPU doesn't support SMM_Code_Chk_En in the first place,
            # or the CPU supports SMM_Code_Chk_En but the BIOS forgot to enable it.
            #
            # In either case, there is nothing that prevents SMM code from executing instructions outside the ranges defined by the SMRRs,
            # so we should at least issue a warning regarding that.
            res = ModuleResult.WARNING

        return res

    def check_SMM_Code_Chk_En(self):
        self.logger.start_test( "SMM_Code_Chk_En (SMM Call-Out) Protection" )

        results = []
        for tid in range(self.cs.msr.get_cpu_thread_count()):
            results.append(self._check_SMM_Code_Chk_En(tid))

        # Check that all CPUs have the same value of MSR_SMM_FEATURE_CONTROL.
        if not all(_ == results[0] for _ in results):
            self.logger.log_failed_check( "MSR_SMM_FEATURE_CONTROL does not have the same value across all CPUs" )
            return ModuleResult.ERROR
        
        res = results[0] 
        if res == ModuleResult.ERROR:
            self.logger.log_failed_check( "SMM_Code_Chk_En is enabled but not locked down" )
        elif res == ModuleResult.WARNING:
            self.logger.warn( """[*] SMM_Code_Chk_En is not enabled.
This can happen either because this feature is not supported by the CPU or because the BIOS forgot to enable it.
Please consult the Intel SDM to determine whether or not your CPU supports SMM_Code_Chk_En.""" )
        else:
            self.logger.log_passed_check( "SMM_Code_Chk_En is enabled and locked down" )

        return res

    # --------------------------------------------------------------------------
    # run( module_argv )
    # Required function: run here all tests from this module
    # --------------------------------------------------------------------------
    def run( self, module_argv ):
        return self.check_SMM_Code_Chk_En()

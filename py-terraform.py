from python_terraform import Terraform
import os

print(os.getcwd())
tf = Terraform(working_dir=os.getcwd())

# Optional: init before validate
return_code, stdout, stderr = tf.init()
print("Init output:\n", stdout)

# Validate the Terraform configuration
return_code, stdout, stderr = tf.validate()
if return_code == 0:
    print("Terraform validation successful ✅")
else:
    print("Terraform validation failed ❌")
    print(stderr)

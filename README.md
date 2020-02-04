Python script that uses the Troposphere library to generate a CloudFormation template that will deploy a broken environment.

Deploy the CloudFormation template and then fix any problems, so you can:
* SSH into the EC2 JumpBox instance and install the latest OS updates.
* From the JumpBox, SSH into the S3 instance, create a text file with your name and upload it to "namebucket" via the CLI
* Upload the index.html file to the "cloudfrontbucket" and have is accessible via the cloudfront url e.g http://d3outmmle9mf6g.cloudfront.net/.....
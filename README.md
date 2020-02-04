Python script that uses the Troposphere library to generate a CloudFormation template that will deploy a broken environment.

Deploy the CloudFormation template and then fix any problems, so you can:
* SSH into the EC2 JumpBox instance and install the latest OS updates.
* From the JumpBox, SSH into the S3 instance. Create a text file with your name and upload it to the "namebucket-*" S3 bucket via the CLI
* Upload the index.html file to the "cloudfrontbucket-*" S3 bucket and have it accessible via the cloudfront distribution url. E.g http://d3outmmle9mf6g.cloudfront.net/.....
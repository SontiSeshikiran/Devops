provider "aws" {
  region = "ap-south-1"
}

resource "aws_security_group" "app_sg" {
  name = "devops-sg"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "app" {
  ami                    = "ami-0f5ee92e2d63afc18"
  instance_type          = "t2.micro"
  key_name               = "devops"
  vpc_security_group_ids = [aws_security_group.app_sg.id]

  tags = {
    Name = "fastapi-devops"
  }
}
variable "namespace" {
    description = "The namespace to deploy the backend resources"
    type = string
}

variable "image_name" {
    description = "The name of the image to deploy"
    type = string
}

variable "replicas" {
    description = "The number of replicas to deploy"
    type = number
    default = 1
}
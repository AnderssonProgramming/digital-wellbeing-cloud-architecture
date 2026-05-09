#!/usr/bin/env pwsh

# CVS Cloud Platform - Local Development & Deployment Helper
# This script deploys the platform to a local Kubernetes cluster (Minikube or Kind)

$namespaces = @("ns-staging", "ns-production")

foreach ($ns in $namespaces) {
    Write-Host "Creating namespace: $ns" -ForegroundColor Cyan
    kubectl create namespace $ns --dry-run=client -o yaml | kubectl apply -f -
}

$services = @("rule-engine", "normalizer", "anonymizer", "inference-svc")

foreach ($svc in $services) {
    Write-Host "Deploying service: $svc" -ForegroundColor Green
    helm upgrade --install $svc "./helm/$svc/" `
        --namespace ns-staging `
        --set image.tag=latest `
        --atomic `
        --timeout 5m
}

Write-Host "`nDeployment complete! Use 'kubectl get pods -n ns-staging' to check status." -ForegroundColor Yellow

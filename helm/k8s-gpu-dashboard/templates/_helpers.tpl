{{/*
Expand the name of the chart.
*/}}
{{- define "k8s-gpu-dashboard.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "k8s-gpu-dashboard.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "k8s-gpu-dashboard.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Backend fullname
*/}}
{{- define "k8s-gpu-dashboard.backend.fullname" -}}
{{- printf "%s-backend" (include "k8s-gpu-dashboard.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Frontend fullname
*/}}
{{- define "k8s-gpu-dashboard.frontend.fullname" -}}
{{- printf "%s-frontend" (include "k8s-gpu-dashboard.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "k8s-gpu-dashboard.labels" -}}
helm.sh/chart: {{ include "k8s-gpu-dashboard.chart" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Backend labels
*/}}
{{- define "k8s-gpu-dashboard.backend.labels" -}}
{{ include "k8s-gpu-dashboard.labels" . }}
app.kubernetes.io/name: {{ include "k8s-gpu-dashboard.name" . }}
app.kubernetes.io/component: backend
{{- end }}

{{/*
Backend selector labels
*/}}
{{- define "k8s-gpu-dashboard.backend.selectorLabels" -}}
app.kubernetes.io/name: {{ include "k8s-gpu-dashboard.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: backend
{{- end }}

{{/*
Frontend labels
*/}}
{{- define "k8s-gpu-dashboard.frontend.labels" -}}
{{ include "k8s-gpu-dashboard.labels" . }}
app.kubernetes.io/name: {{ include "k8s-gpu-dashboard.name" . }}
app.kubernetes.io/component: frontend
{{- end }}

{{/*
Frontend selector labels
*/}}
{{- define "k8s-gpu-dashboard.frontend.selectorLabels" -}}
app.kubernetes.io/name: {{ include "k8s-gpu-dashboard.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: frontend
{{- end }}

{{/*
Create the name of the service account to use (backend)
*/}}
{{- define "k8s-gpu-dashboard.backend.serviceAccountName" -}}
{{- if .Values.backend.serviceAccount.create }}
{{- default (include "k8s-gpu-dashboard.backend.fullname" .) .Values.backend.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.backend.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Backend internal URL for nginx proxy (auto-computed)
*/}}
{{- define "k8s-gpu-dashboard.backend.internalUrl" -}}
{{- printf "%s:%s" (include "k8s-gpu-dashboard.backend.fullname" .) (toString .Values.backend.service.port) }}
{{- end }}

{{/*
通用辅助模板：名称/全名/标签选择器
*/}}
{{- define "sm-workflow-approval.name" -}}
{{ default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "sm-workflow-approval.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end -}}
{{- end }}

{{- define "sm-workflow-approval.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end }}

{{- define "sm-workflow-approval.commonLabels" -}}
app.kubernetes.io/name: {{ include "sm-workflow-approval.name" . }}
helm.sh/chart: {{ include "sm-workflow-approval.chart" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "sm-workflow-approval.selectorLabels" -}}
app.kubernetes.io/name: {{ include "sm-workflow-approval.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "sm-workflow-approval.serviceAccountName" -}}
{{ default (printf "%s-sa" (include "sm-workflow-approval.fullname" .)) .Values.serviceAccount.name }}
{{- end }}

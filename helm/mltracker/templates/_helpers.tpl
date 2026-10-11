{{- define "mltracker.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "mltracker.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name (include "mltracker.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "mltracker.labels" -}}
app.kubernetes.io/name: {{ include "mltracker.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- end -}}

{{- /* Selector labels must never include version or chart: they are immutable
       on a Deployment, so a chart bump would make the upgrade fail. */ -}}
{{- define "mltracker.selectorLabels" -}}
app.kubernetes.io/name: {{ include "mltracker.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "mltracker.postgresHost" -}}
{{- printf "%s-postgres" (include "mltracker.fullname" .) -}}
{{- end -}}

{{- define "mltracker.secretName" -}}
{{- if .Values.postgres.existingSecret -}}
{{- .Values.postgres.existingSecret -}}
{{- else -}}
{{- printf "%s-db" (include "mltracker.fullname" .) -}}
{{- end -}}
{{- end -}}

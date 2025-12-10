using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Net.Http;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using H3LIX.Networking.Dto;
using Newtonsoft.Json;
using UnityEngine;

namespace H3LIX.Networking
{
    public class H3LIXClient : IDisposable
    {
        private readonly HttpClient _http;
        private readonly Uri _baseUri;
        private readonly string _streamPath;
        private readonly string _authToken;
        private ClientWebSocket _ws;
        private CancellationTokenSource _cts;

        public readonly ConcurrentQueue<AnyTelemetryEnvelope> Inbound = new();

        public H3LIXClient(H3LIXClientConfig config)
        {
            _baseUri = new Uri(config.baseUrl.TrimEnd('/'));
            _streamPath = config.streamPath;
            _authToken = config.authToken;
            _http = new HttpClient { Timeout = TimeSpan.FromSeconds(config.httpTimeoutSeconds) };
            if (!string.IsNullOrEmpty(_authToken))
            {
                _http.DefaultRequestHeaders.Add("Authorization", $"Bearer {_authToken}");
            }
        }

        public async Task<List<SessionSummary>> FetchSessions()
        {
            var url = new Uri(_baseUri, "/v1/sessions");
            var json = await _http.GetStringAsync(url);
            return JsonConvert.DeserializeObject<List<SessionSummary>>(json) ?? new List<SessionSummary>();
        }

        public async Task<SnapshotResponse> FetchSnapshot(string sessionId)
        {
            var url = new Uri(_baseUri, $"/v1/sessions/{sessionId}/snapshot");
            var json = await _http.GetStringAsync(url);
            return JsonConvert.DeserializeObject<SnapshotResponse>(json);
        }

        public async Task<ReplayResponse> FetchReplay(string sessionId, int fromMs, int toMs)
        {
            var url = new Uri(_baseUri, $"/v1/sessions/{sessionId}/replay?from_ms={fromMs}&to_ms={toMs}");
            var json = await _http.GetStringAsync(url);
            return JsonConvert.DeserializeObject<ReplayResponse>(json);
        }

        public async Task<List<Cohort>> FetchCohorts()
        {
            var url = new Uri(_baseUri, "/v1/cohorts");
            var json = await _http.GetStringAsync(url);
            return JsonConvert.DeserializeObject<List<Cohort>>(json) ?? new List<Cohort>();
        }

        public async Task<CohortNoeticSummary> FetchCohortNoeticSummary(string cohortId, int fromMs, int toMs, int binMs = 1000)
        {
            var url = new Uri(_baseUri, $"/v1/cohorts/{cohortId}/noetic-summary?from_ms={fromMs}&to_ms={toMs}&bin_ms={binMs}");
            var json = await _http.GetStringAsync(url);
            return JsonConvert.DeserializeObject<CohortNoeticSummary>(json);
        }

        public async Task<CohortMpgEchoResponse> FetchCohortMpgEchoes(string cohortId, int fromMs, int toMs, double minConsistency = 0.7)
        {
            var url = new Uri(_baseUri, $"/v1/cohorts/{cohortId}/mpg-echoes?from_ms={fromMs}&to_ms={toMs}&min_consistency={minConsistency}");
            var json = await _http.GetStringAsync(url);
            return JsonConvert.DeserializeObject<CohortMpgEchoResponse>(json);
        }

        public async Task<string> Health()
        {
            var url = new Uri(_baseUri, "/health");
            return await _http.GetStringAsync(url);
        }

        public async Task OpenStream(string sessionId, MessageType[] messageTypes = null)
        {
            _cts?.Cancel();
            _cts = new CancellationTokenSource();
            _ws?.Dispose();
            _ws = new ClientWebSocket();
            if (!string.IsNullOrEmpty(_authToken))
            {
                _ws.Options.SetRequestHeader("Authorization", $"Bearer {_authToken}");
            }
            var streamUri = new Uri(_baseUri, _streamPath);
            await _ws.ConnectAsync(streamUri, _cts.Token);

            // subscribe
            var payload = new
            {
                type = "subscribe",
                session_id = sessionId,
                message_types = messageTypes != null ? Array.ConvertAll(messageTypes, t => ToRaw(t)) : (object)MessageTypeValues.All
            };
            var subJson = JsonConvert.SerializeObject(payload);
            var subBuffer = Encoding.UTF8.GetBytes(subJson);
            await _ws.SendAsync(subBuffer, WebSocketMessageType.Text, true, _cts.Token);

            _ = Task.Run(() => ListenLoop(_cts.Token), _cts.Token);
        }

        private async Task ListenLoop(CancellationToken ct)
        {
            while (!ct.IsCancellationRequested && _ws != null && _ws.State == WebSocketState.Open)
            {
                try
                {
                    using var ms = new MemoryStream();
                    WebSocketReceiveResult result;
                    do
                    {
                        var buffer = new ArraySegment<byte>(new byte[1024 * 8]);
                        result = await _ws.ReceiveAsync(buffer, ct);

                        if (result.MessageType == WebSocketMessageType.Close)
                        {
                            await _ws.CloseAsync(WebSocketCloseStatus.NormalClosure, "closing", CancellationToken.None);
                            return;
                        }

                        ms.Write(buffer.Array, buffer.Offset, result.Count);
                    } while (!result.EndOfMessage && !ct.IsCancellationRequested);

                    var json = Encoding.UTF8.GetString(ms.ToArray());
                    var env = JsonConvert.DeserializeObject<AnyTelemetryEnvelope>(json);
                    if (env != null) Inbound.Enqueue(env);
                }
                catch (OperationCanceledException)
                {
                    break;
                }
                catch (Exception ex)
                {
                    Debug.LogWarning($"Failed to decode envelope: {ex}");
                    break;
                }
            }
        }

        public async Task CloseStream()
        {
            try
            {
                _cts?.Cancel();
                if (_ws != null && _ws.State == WebSocketState.Open)
                {
                    await _ws.CloseAsync(WebSocketCloseStatus.NormalClosure, "client closing", CancellationToken.None);
                }
            }
            catch (Exception) { }
            finally
            {
                _ws?.Dispose();
                _ws = null;
            }
        }

        public void Dispose()
        {
            _cts?.Cancel();
            _ws?.Dispose();
            _http?.Dispose();
        }

        private static string ToRaw(MessageType t) =>
            t switch
            {
                MessageType.SomaticState => "somatic_state",
                MessageType.SymbolicState => "symbolic_state",
                MessageType.NoeticState => "noetic_state",
                MessageType.DecisionCycle => "decision_cycle",
                MessageType.MpgDelta => "mpg_delta",
                MessageType.RogueVariableEvent => "rogue_variable_event",
                MessageType.MufsEvent => "mufs_event",
                _ => "somatic_state"
            };
    }

    internal static class MessageTypeValues
    {
        public static readonly string[] All = new[]
        {
            "somatic_state", "symbolic_state", "noetic_state", "decision_cycle", "mpg_delta", "rogue_variable_event", "mufs_event"
        };
    }
}

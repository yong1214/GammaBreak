import Foundation
import Combine

enum APIError: LocalizedError {
    case badURL
    case http(Int, String)
    case decoding(Error)
    case transport(Error)

    var errorDescription: String? {
        switch self {
        case .badURL: return "Invalid backend URL"
        case .http(let code, let body): return "HTTP \(code): \(body)"
        case .decoding(let err): return "Decoding failed: \(err.localizedDescription)"
        case .transport(let err): return "Network error: \(err.localizedDescription)"
        }
    }
}

@MainActor
final class APIClient: ObservableObject {
    private let settings: AppSettings
    private let session: URLSession
    private let decoder: JSONDecoder

    init(settings: AppSettings) {
        self.settings = settings
        let cfg = URLSessionConfiguration.default
        cfg.timeoutIntervalForRequest = 20
        self.session = URLSession(configuration: cfg)

        let decoder = JSONDecoder()
        let dateFormatter = DateFormatter()
        dateFormatter.dateFormat = "yyyy-MM-dd"
        dateFormatter.locale = Locale(identifier: "en_US_POSIX")
        decoder.dateDecodingStrategy = .formatted(dateFormatter)
        self.decoder = decoder
    }

    func optionChain(symbol: String, expiry: Date? = nil, strikeWindow: Int = 10) async throws -> OptionChain {
        var query: [URLQueryItem] = [URLQueryItem(name: "strike_window", value: "\(strikeWindow)")]
        if let expiry { query.append(URLQueryItem(name: "expiry", value: Self.dateFmt.string(from: expiry))) }
        return try await get("/api/chain/\(symbol)", query: query)
    }

    func gammaProfile(symbol: String) async throws -> GammaProfile {
        try await get("/api/gamma/\(symbol)")
    }

    func predict(symbol: String, horizonMinutes: Int = 60) async throws -> PricePrediction {
        try await get("/api/predict/\(symbol)", query: [URLQueryItem(name: "horizon_minutes", value: "\(horizonMinutes)")])
    }

    func quote(symbol: String) async throws -> [String: AnyCodable] {
        try await get("/api/quote/\(symbol)")
    }

    private func get<T: Decodable>(_ path: String, query: [URLQueryItem] = []) async throws -> T {
        guard var components = URLComponents(string: settings.backendURL) else {
            throw APIError.badURL
        }
        components.path = path
        if !query.isEmpty { components.queryItems = query }
        guard let url = components.url else { throw APIError.badURL }

        var req = URLRequest(url: url)
        req.httpMethod = "GET"
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        if !settings.authToken.isEmpty {
            req.setValue("Bearer \(settings.authToken)", forHTTPHeaderField: "Authorization")
        }

        let (data, response): (Data, URLResponse)
        do {
            (data, response) = try await session.data(for: req)
        } catch {
            throw APIError.transport(error)
        }

        guard let http = response as? HTTPURLResponse else {
            throw APIError.http(-1, "non-HTTP response")
        }
        guard (200..<300).contains(http.statusCode) else {
            let body = String(data: data, encoding: .utf8) ?? ""
            throw APIError.http(http.statusCode, body)
        }

        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            throw APIError.decoding(error)
        }
    }

    private static let dateFmt: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "yyyy-MM-dd"
        f.locale = Locale(identifier: "en_US_POSIX")
        return f
    }()
}

struct AnyCodable: Codable {
    let value: Any?
    init(from decoder: Decoder) throws {
        let c = try decoder.singleValueContainer()
        if c.decodeNil() { value = nil }
        else if let v = try? c.decode(Bool.self) { value = v }
        else if let v = try? c.decode(Double.self) { value = v }
        else if let v = try? c.decode(String.self) { value = v }
        else if let v = try? c.decode([AnyCodable].self) { value = v.map { $0.value } }
        else if let v = try? c.decode([String: AnyCodable].self) { value = v.mapValues { $0.value } }
        else { value = nil }
    }
    func encode(to encoder: Encoder) throws {
        var c = encoder.singleValueContainer()
        if value == nil { try c.encodeNil() }
    }
}

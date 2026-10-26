// The colosseum stage (BlenderSource/arena.py, Built-in RP): one lit surface shader for every arena material.
// Colour comes from vertex colours; vertex alpha says how much a vertex may move:
//  - _Sway    banners and flags ripple in the wind
//  - _Bob     the crowd: heads and raised arms bob in a wave running round the stands
//  - _Flicker flame tips lick and stretch (with _Emission)
//  - _NoiseStrength faint world-space mottling for the marble
// All motion is in the vertex shader: no bones, no particles, one draw call per material (cheap on iGPU).
Shader "Chess/Arena"
{
    Properties
    {
        _Glossiness ("Smoothness", Range(0, 1)) = 0.3
        _Metallic ("Metallic", Range(0, 1)) = 0
        _NoiseStrength ("Noise Strength", Range(0, 1)) = 0
        _NoiseScale ("Noise Scale", Float) = 2.2
        _Sway ("Cloth Sway", Float) = 0
        _Bob ("Crowd Bob", Float) = 0
        _Flicker ("Flame Flicker", Float) = 0
        _Emission ("Emission", Float) = 0
    }
    SubShader
    {
        Tags { "RenderType" = "Opaque" }
        Cull Off

        CGPROGRAM
        #pragma surface surf Standard fullforwardshadows addshadow vertex:vert
        #pragma target 3.0

        struct Input { float4 color : COLOR; float3 worldPos; };

        half _Glossiness, _Metallic, _NoiseStrength, _NoiseScale, _Sway, _Bob, _Flicker, _Emission;

        void vert(inout appdata_full v)
        {
            float w = v.color.a;
            float3 wp = mul(unity_ObjectToWorld, v.vertex).xyz;
            float t = _Time.y;
            float ph = dot(wp, float3(0.7, 0.31, 0.53));
            float3 off = 0;
            off += _Sway * w * float3(sin(t * 1.7 + ph), 0, cos(t * 1.3 + ph * 1.3)) * 0.09;
            float ang = atan2(wp.z, wp.x);                        // a wave running round the stands
            float wave = max(0, sin(ang * 6 - t * 2.2)) * 0.12 + max(0, sin(t * 7 + ang * 40)) * 0.03;
            off.y += _Bob * w * wave;
            off += _Flicker * w * float3(sin(t * 13 + ph * 5) * 0.04, sin(t * 17 + ph * 3) * 0.07, cos(t * 11 + ph * 7) * 0.04);
            v.vertex.xyz += mul((float3x3)unity_WorldToObject, off);
        }

        float hash(float3 p) { p = frac(p * 0.3183099 + 0.1); p *= 17.0; return frac(p.x * p.y * p.z * (p.x + p.y + p.z)); }
        float vnoise(float3 x)
        {
            float3 i = floor(x), f = frac(x); f = f * f * (3 - 2 * f);
            return lerp(lerp(lerp(hash(i), hash(i + float3(1, 0, 0)), f.x), lerp(hash(i + float3(0, 1, 0)), hash(i + float3(1, 1, 0)), f.x), f.y),
                        lerp(lerp(hash(i + float3(0, 0, 1)), hash(i + float3(1, 0, 1)), f.x), lerp(hash(i + float3(0, 1, 1)), hash(i + float3(1, 1, 1)), f.x), f.y), f.z);
        }

        void surf(Input IN, inout SurfaceOutputStandard o)
        {
            float3 c = IN.color.rgb;
            #ifndef UNITY_COLORSPACE_GAMMA
            c = GammaToLinearSpace(c);
            #endif
            float n = vnoise(IN.worldPos * _NoiseScale) * 0.6 + vnoise(IN.worldPos * _NoiseScale * 4.1) * 0.4;
            c *= 1 - _NoiseStrength * 0.25 * n;
            o.Albedo = c;
            o.Metallic = _Metallic;
            o.Smoothness = _Glossiness;
            o.Emission = c * _Emission;
        }
        ENDCG
    }
}

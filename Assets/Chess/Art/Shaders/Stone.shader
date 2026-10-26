// Carved-stone statue surface (Built-in RP).
//  - mottling + faint veins from 3D value noise, sampled in bind-pose space (UV2, see PieceImporter)
//    or world space (_WorldSpace = 1, for the board)
//  - _Crumble 0..~0.65: the stone is eaten away in chunks with dark cracked rims (death)
//  - _Fade 1..0: screen-door dissolve so rubble can thin out and vanish while staying opaque (cheap on iGPU)
Shader "Chess/Stone"
{
    Properties
    {
        _Color ("Color", Color) = (0.79, 0.78, 0.75, 1)
        _Glossiness ("Smoothness", Range(0, 1)) = 0.5
        _NoiseScale ("Noise Scale", Float) = 38
        _NoiseStrength ("Noise Strength", Range(0, 1)) = 1
        _WorldSpace ("World Space Noise", Float) = 0
        _Crumble ("Crumble", Range(0, 1)) = 0
        _Fade ("Fade", Range(0, 1)) = 1
    }
    SubShader
    {
        Tags { "RenderType" = "Opaque" }
        LOD 200

        CGPROGRAM
        #pragma surface surf Standard fullforwardshadows addshadow vertex:vert
        #pragma target 3.0

        struct Input
        {
            float3 stonePos;
            float4 screenPos;
        };

        fixed4 _Color;
        half _Glossiness;
        float _NoiseScale, _NoiseStrength, _WorldSpace, _Crumble, _Fade;

        void vert(inout appdata_full v, out Input o)
        {
            UNITY_INITIALIZE_OUTPUT(Input, o);
            o.stonePos = lerp(v.texcoord2.xyz, mul(unity_ObjectToWorld, v.vertex).xyz, _WorldSpace);
        }

        float h3(float3 p) { p = frac(p * 0.3183099 + 0.1); p *= 17.0; return frac(p.x * p.y * p.z * (p.x + p.y + p.z)); }
        float n3(float3 x)
        {
            float3 i = floor(x), f = frac(x); f = f * f * (3 - 2 * f);
            return lerp(lerp(lerp(h3(i), h3(i + float3(1, 0, 0)), f.x), lerp(h3(i + float3(0, 1, 0)), h3(i + float3(1, 1, 0)), f.x), f.y),
                        lerp(lerp(h3(i + float3(0, 0, 1)), h3(i + float3(1, 0, 1)), f.x), lerp(h3(i + float3(0, 1, 1)), h3(i + float3(1, 1, 1)), f.x), f.y), f.z);
        }
        float fbm(float3 p) { float a = 0.5, s = 0; for (int k = 0; k < 4; k++) { s += a * n3(p); p *= 2.03; a *= 0.5; } return s; }

        void surf(Input IN, inout SurfaceOutputStandard o)
        {
            // screen-door fade: 4x4 ordered dither against _Fade
            if (_Fade < 0.999)
            {
                float2 px = floor(IN.screenPos.xy / max(IN.screenPos.w, 1e-5) * _ScreenParams.xy);
                const float4x4 bayer = float4x4(0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5) / 16.0;
                clip(_Fade - bayer[(uint)px.x % 4][(uint)px.y % 4] - 0.001);
            }
            float3 p = IN.stonePos;
            float rim = 0;
            if (_Crumble > 0)
            {
                float cr = fbm(p * 9.0);
                clip(cr - _Crumble);
                rim = smoothstep(_Crumble + 0.07, _Crumble, cr);
            }
            float3 sp = p * _NoiseScale;
            float n = fbm(sp);
            float vein = 1 - smoothstep(0, 0.06, abs(sin(sp.x * 0.35 + sp.y * 0.2 + fbm(sp * 0.5) * 5)));
            float3 c = _Color.rgb * lerp(1, 0.8 + 0.4 * n - 0.18 * vein, _NoiseStrength);
            o.Albedo = c * lerp(1, 0.3, rim);
            o.Smoothness = saturate(_Glossiness + (n - 0.5) * 0.25 * _NoiseStrength);
            o.Metallic = 0;
        }
        ENDCG
    }
    FallBack "Diffuse"
}

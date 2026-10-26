// Golden-hour sky for the colosseum (skybox material, Built-in RP): blue zenith to a warm hazy horizon, a low
// sun with a wide glow, and soft drifting clouds lit gold on the sun side. Procedural, one cheap pass.
Shader "Chess/SunsetSky"
{
    Properties
    {
        _Top ("Zenith", Color) = (0.22, 0.42, 0.72, 1)
        _Horizon ("Horizon", Color) = (1.0, 0.74, 0.46, 1)
        _SunDir ("Sun Direction", Vector) = (0.55, 0.2, -0.8, 0)
        _SunColor ("Sun Color", Color) = (1, 0.86, 0.6, 1)
        _SunSize ("Sun Radius (rad)", Float) = 0.035
        _Clouds ("Clouds", Float) = 0.8
    }
    SubShader
    {
        Tags { "Queue" = "Background" "RenderType" = "Background" "PreviewType" = "Skybox" }
        Cull Off ZWrite Off

        Pass
        {
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "UnityCG.cginc"

            fixed4 _Top, _Horizon, _SunColor;
            float4 _SunDir;
            float _SunSize, _Clouds;

            struct v2f { float4 pos : SV_POSITION; float3 dir : TEXCOORD0; };

            v2f vert(appdata_base v)
            {
                v2f o;
                o.pos = UnityObjectToClipPos(v.vertex);
                o.dir = v.vertex.xyz;
                return o;
            }

            float hash(float2 p) { return frac(sin(dot(p, float2(127.1, 311.7))) * 43758.5453); }
            float vnoise(float2 x)
            {
                float2 i = floor(x), f = frac(x); f = f * f * (3 - 2 * f);
                return lerp(lerp(hash(i), hash(i + float2(1, 0)), f.x), lerp(hash(i + float2(0, 1)), hash(i + float2(1, 1)), f.x), f.y);
            }
            float fbm(float2 x) { return vnoise(x) * 0.5 + vnoise(x * 2.1) * 0.3 + vnoise(x * 4.3) * 0.2; }

            fixed4 frag(v2f i) : SV_Target
            {
                float3 d = normalize(i.dir);
                float h = saturate(d.y);
                float3 s = normalize(_SunDir.xyz);
                float sd = saturate(dot(d, s));
                float3 c = lerp(_Horizon.rgb, _Top.rgb, pow(h, 0.45));
                c = lerp(c, _Horizon.rgb * 1.05, pow(sd, 6) * (1 - h) * 0.8);   // the horizon burns brighter towards the sun
                if (d.y < 0) c = _Horizon.rgb * 0.85;

                // clouds on a flat layer above: projected, drifting slowly
                float2 uv = d.xz / max(0.08, d.y) * 0.35 + _Time.y * float2(0.004, 0.002);
                float cl = smoothstep(0.5, 0.78, fbm(uv * 1.3)) * smoothstep(0.02, 0.2, d.y) * _Clouds;
                float3 cloudCol = lerp(float3(0.95, 0.9, 0.86), _SunColor.rgb * 1.2, pow(sd, 3));
                cloudCol *= lerp(0.75, 1.1, fbm(uv * 3.1 + 5));
                c = lerp(c, cloudCol, cl);

                // the sun: glow and disc (dimmed where a cloud passes in front)
                float ang = acos(clamp(dot(d, s), -1, 1));
                c += _SunColor.rgb * (0.5 * exp(-ang * 7) + 0.15 * exp(-ang * 1.8));
                c = lerp(c, _SunColor.rgb * 2.2, smoothstep(_SunSize, _SunSize * 0.85, ang) * (1 - cl * 0.7));
                return fixed4(c, 1);
            }
            ENDCG
        }
    }
}
